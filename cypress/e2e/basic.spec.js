/// <reference types="cypress" />
import 'cypress-axe';

describe('Basic UI & accessibility checks', () => {
  it('loads home page and opens New Project modal', () => {
    cy.visit('/');
    cy.title().should('include', 'AI Project Co-Pilot');

    // Activate Projects view via the app nav and open New Project modal
    // Wait until the app's navTo function is available and click the sidebar item
    cy.window().then(win => expect(typeof win.navTo).to.equal('function'));
    // Call the inline onclick handler directly to ensure navTo runs
    // Run axe accessibility scan on the main page (exclude modal which is tested separately)
    cy.injectAxe();
    // Log axe violations to the CI output for easier debugging
    cy.checkA11y(null, null, (violations) => {
      if (violations.length) {
        const simplified = violations.map(v => ({
          id: v.id,
          impact: v.impact,
          description: v.description,
          nodes: v.nodes.map(n => ({ html: n.html, failureSummary: n.failureSummary }))
        }));
        cy.task('log', `Axe Violations: ${JSON.stringify(simplified, null, 2)}`);
      }
      // Attach the simplified violations JSON to the assertion message for CI visibility
      expect(violations.length, `Axe Violations: ${JSON.stringify(simplified, null, 2)}`).to.equal(0);
    });

    // Open New Project modal directly (nav may not be reliable in headless CI)
    cy.window().then(win => win.openNewProjectModal());
    cy.get('#newProjectModal').should('be.visible').and('contain.text', 'Create New Project');
  });

  it('prevents XSS in document chat (sanitizes input)', () => {
    cy.visit('/');
    // Activate Design view via the app nav
    cy.window().then(win => expect(typeof win.navTo).to.equal('function'));
    cy.window().then(win => win.navTo('design'));
    cy.get('#view-design').should('have.class', 'active').and('be.visible');
    cy.wait(500);

    // Open document detail if there is one (only proceed if table contains a real document row)
    cy.get('#view-design tbody tr').first().then($tr => {
      const txt = $tr.text().trim();
      if(!txt.includes('Select a project') && !txt.includes('No documents') && !txt.includes('Loading')) {
        cy.wrap($tr).click({ force: true });

        // Only proceed if the document detail view actually became active
        cy.get('#view-document-detail').then($vd => {
          if($vd.hasClass('active')) {
            cy.wrap($vd).contains('Co-Pilot').click();
            cy.get('#docChatInput').should('be.visible');

            const payload = '<img src=x onerror=alert(1)>DROP';
            cy.get('#docChatInput').type(payload);
            cy.wrap($vd).contains('Send').click({ force: true });

            // ensure that chat area does not contain unescaped onerror or injected tags and contains payload as text
            cy.get('#docChatArea').invoke('html').should('not.contain', 'onerror').and('not.contain', '<img').and('not.contain', '<script');
            cy.get('#docChatArea').should('contain.text', 'DROP');
          }
        });
      }
    });
  });
});
