// Run axe-core (WCAG 2.0/2.1/2.2 A, AA and AAA rules, plus best practices) on each page, light and dark.
const CDP = require('chrome-remote-interface');
const fs = require('fs');
const axeSource = fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
const [,, port, base, sessionid, ...paths] = process.argv;
(async () => {
  const client = await CDP({ port: +port });
  const { Page, Runtime, Network, Emulation } = client;
  await Promise.all([Page.enable(), Runtime.enable(), Network.enable()]);
  if (sessionid && sessionid !== '-') await Network.setCookie({ name: 'sessionid', value: sessionid, url: base });
  const results = {};
  for (const scheme of ['light', 'dark']) {
    await Emulation.setEmulatedMedia({ features: [{ name: 'prefers-color-scheme', value: scheme }] });
    for (const p of paths) {
      await Page.navigate({ url: base + p });
      await Page.loadEventFired();
      await new Promise(r => setTimeout(r, 300));
      await Runtime.evaluate({ expression: axeSource });
      const { result } = await Runtime.evaluate({ awaitPromise: true, returnByValue: true, expression: `
        axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a','wcag2aa','wcag2aaa','wcag21a','wcag21aa','wcag22aa','best-practice'] } })
          .then(r => ({ url: location.pathname + location.search, violations: r.violations.map(v => ({ id: v.id, impact: v.impact, help: v.help,
             nodes: v.nodes.slice(0, 3).map(n => n.target.join(' ') + ' :: ' + (n.failureSummary || '').split('\\n').slice(1,2).join(' ')) , count: v.nodes.length })) }))` });
      results[scheme + ' ' + p] = result.value;
    }
  }
  console.log(JSON.stringify(results, null, 1));
  await client.close();
})().catch(e => { console.error(e); process.exit(1); });
