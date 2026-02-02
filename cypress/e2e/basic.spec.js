/// <reference types="cypress" />
import 'cypress-axe';

describe('Basic UI & accessibility checks', () => {
  it('loads home page and opens New Project modal', () => {
    cy.visit('/');
    cy.title().should('include', 'AI Project Co-Pilot');

    // Make sure Projects view is active then open New Project modal
    cy.contains('Projects').click({ force: true });
    cy.contains('+ New Project').click();
    cy.get('[role="dialog"]').should('be.visible');
    cy.get('[role="dialog"]').should('have.attr', 'aria-modal', 'true');

    // Run axe accessibility scan
    cy.injectAxe();
    cy.checkA11y();
  });

  it('prevents XSS in document chat (sanitizes input)', () => {
    cy.visit('/');
    // Ensure Design view is active before trying to open a document
    cy.contains('Design').click({ force: true });

    // Open document detail if there is one
    cy.get('table').then($tbl => {
      // try to open first document row
      if($tbl.find('tbody tr').length) {
        cy.get('tbody tr').first().click({ force: true });
        cy.get('#docChatInput').should('exist');
        const payload = '<img src=x onerror=alert(1)>DROP';
        cy.get('#docChatInput').type(payload);
        cy.contains('Send').click({ force: true });
        // ensure that chat area does not contain unescaped onerror or injected tags and contains payload as text
        cy.get('#docChatArea').invoke('html').should('not.contain', 'onerror').and('not.contain', '<img').and('not.contain', '<script');
        cy.get('#docChatArea').should('contain.text', 'DROP');
      }
    });
  });
});
