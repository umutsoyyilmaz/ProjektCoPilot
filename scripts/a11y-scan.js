const puppeteer = require('puppeteer');
const axeCore = require('axe-core');

(async () => {
  const browser = await puppeteer.launch({ args: ['--no-sandbox', '--disable-setuid-sandbox'] });
  const page = await browser.newPage();
  await page.goto('http://127.0.0.1:8080', { waitUntil: 'networkidle2' });

  // Inject axe-core into the page and run
  await page.evaluate(axeSource => {
    const script = document.createElement('script');
    script.text = axeSource;
    document.head.appendChild(script);
  }, axeCore.source);

  const results = await page.evaluate(async () => {
    return await axe.run();
  });

  if (results.violations && results.violations.length > 0) {
    const simplified = results.violations.map(v => ({
      id: v.id,
      impact: v.impact,
      description: v.description,
      nodes: v.nodes.map(n => ({ html: n.html, failureSummary: n.failureSummary }))
    }));
    console.error('A11Y Violations:', JSON.stringify(simplified, null, 2));
    await browser.close();
    process.exit(1);
  }

  console.log('No accessibility violations found');
  await browser.close();
  process.exit(0);
})().catch(e => {
  console.error('A11Y scan error', e);
  process.exit(2);
});