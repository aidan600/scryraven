// The document and citation destinations are ready before any print events.
const printButton = document.querySelector('.print-toolbar button');
printButton.hidden = false;
printButton.addEventListener('click', () => window.print());
