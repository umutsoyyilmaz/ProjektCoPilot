/// <reference types="cypress" />
import 'cypress-axe';

describe('Basic UI & accessibility checks', () => {
  it('loads home page and opens New Project modal', () => {
    cy.visit('/');
    cy.title().should('include', 'AI Project Co-Pilot');

    // Activate Projects view via the app nav and open New Project modal
    // Wait until the app's navTo function is available and click the sidebar item
    cy.window().then(win => expect(typeof win.navTo).to.equal('function'));
    cy.get('.nav-item').contains('Projects').click();
    cy.get('#view-projects').should('have.class', 'active').and('be.visible');
    cy.get('#view-projects').contains('+ New Project').click();
    cy.get('[role="dialog"]').should('be.visible');
    cy.get('[role="dialog"]').should('have.attr', 'aria-modal', 'true');

    // Run axe accessibility scan
    cy.injectAxe();
    cy.checkA11y();
  });

  it('prevents XSS in document chat (sanitizes input)', () => {
    cy.visit('/');
    // Activate Design view via the app nav
    cy.window().then(win => expect(typeof win.navTo).to.equal('function'));
    cy.get('.nav-item').contains('Design').click();
    cy.get('#view-design').should('have.class', 'active').and('be.visible');
    cy.wait(500);

    // Open document detail if there is one (only proceed if table contains a real document row)
    cy.get('#view-design tbody tr').first().then($tr => {
      const txt = $tr.text().trim();
      if(!txt.includes('Select a project') && !txt.includes('No documents') && !txt.includes('Loading')) {
        cy.wrap($tr).click({ force: true });

        // Switch to Co-Pilot tab inside document detail and ensure chat input is visible
        cy.get('#view-document-detail').should('have.class', 'active');
        cy.get('#view-document-detail').contains('Co-Pilot').click();
        cy.get('#docChatInput').should('be.visible');

        const payload = '<img src=x onerror=alert(1)>DROP';
        cy.get('#docChatInput').type(payload);
        cy.get('#view-document-detail').contains('Send').click({ force: true });

        // ensure that chat area does not contain unescaped onerror or injected tags and contains payload as text
        cy.get('#docChatArea').invoke('html').should('not.contain', 'onerror').and('not.contain', '<img').and('not.contain', '<script');
        cy.get('#docChatArea').should('contain.text', 'DROP');
      }
    });
  });
});
