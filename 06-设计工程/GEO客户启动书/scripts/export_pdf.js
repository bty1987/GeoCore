// GEO 文档 · HTML → A4 PDF 导出（V2 咨询报告体 · 含每页运行页脚）
// 用法: node export_pdf.js [源HTML] [输出PDF] [页脚文档名]
// 默认: 启动书 v2
const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const srcArg = process.argv[2] || '../design-demos/v2-consulting-report.html';
  const outArg = process.argv[3] || '../GEO客户启动书-v2咨询报告体.pdf';
  const docLabel = process.argv[4] || '项目启动文档';

  const src = 'file://' + path.resolve(__dirname, srcArg);
  const out = path.resolve(__dirname, outArg);

  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto(src, { waitUntil: 'networkidle' });
  await page.pdf({
    path: out,
    format: 'A4',
    printBackground: true,
    // 顶部 8mm / 底部 16mm 与 HTML 内 @page 一致，底部留给运行页脚
    margin: { top: '8mm', right: 0, bottom: '16mm', left: 0 },
    scale: 1,
    displayHeaderFooter: true,
    headerTemplate: '<div></div>',
    footerTemplate: `
      <div style="width:100%; padding:0 13mm 0; font-family:-apple-system,'PingFang SC',sans-serif;
                  font-size:8px; color:#7E93A2; display:flex; justify-content:space-between;">
        <span>【服务方名称】 · AI 搜索优化（GEO）服务 · ${docLabel}</span>
        <span>第 <span class="pageNumber"></span> 页 / 共 <span class="totalPages"></span> 页</span>
      </div>`,
  });
  await browser.close();
  console.log('PDF written:', out);
})();
