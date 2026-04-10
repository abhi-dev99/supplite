import { useEffect, useMemo, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { fetchWeeklyBrief } from '../api/weeklyBriefApi';

const METROS = [
  'Atlanta',
  'Chicago',
  'Dallas',
  'Denver',
  'Houston',
  'Los Angeles',
  'Miami',
  'New York',
  'Phoenix',
  'San Francisco',
  'Seattle',
];

function riskColor(risk) {
  if (risk === 'STOCKOUT_RISK') return 'var(--color-stockout-text)';
  if (risk === 'OVERSTOCK_RISK') return 'var(--color-overstock-text)';
  if (risk === 'WATCH') return 'var(--color-watch-text)';
  return 'var(--color-ok-text)';
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString();
}

function sectionInsight(title, body) {
  return (
    <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.92rem', lineHeight: 1.55, marginTop: '10px' }}>
      <strong style={{ color: 'var(--color-text-primary)' }}>{title}:</strong> {body}
    </div>
  );
}

function EmptyChartState({ message }) {
  return (
    <div
      style={{
        minHeight: '250px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'var(--color-text-secondary)',
        border: '1px dashed var(--color-surface-hover)',
        borderRadius: '12px',
        background: 'var(--color-surface)',
        padding: '20px',
        textAlign: 'center',
      }}
    >
      {message}
    </div>
  );
}

function parseMarkdownTableRow(line) {
  return line
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((cell) => cell.trim());
}

function isMarkdownTableSeparator(line) {
  return /^\s*\|?(\s*:?-{3,}:?\s*\|)+\s*$/.test(line.trim());
}

function cleanMarkdownInline(text) {
  return String(text || '')
    .replace(/^[-*+]\s+/g, '')
    .replace(/\[(?: |x|X)\]\s*/g, '')
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/__(.*?)__/g, '$1')
    .replace(/\*(.*?)\*/g, '$1')
    .replace(/_(.*?)_/g, '$1')
    .replace(/~~(.*?)~~/g, '$1')
    .replace(/`([^`]*)`/g, '$1')
    .replace(/\s+/g, ' ')
    .trim();
}

function cleanMarkdownKeepBold(text) {
  return String(text || '')
    .replace(/^[-*+]\s+/g, '')
    .replace(/\[(?: |x|X)\]\s*/g, '')
    .replace(/`([^`]*)`/g, '$1')
    .replace(/~~(.*?)~~/g, '$1')
    .replace(/\s+/g, ' ')
    .trim();
}

function parseInlineRuns(text) {
  const normalized = cleanMarkdownKeepBold(text).replace(/__(.*?)__/g, '**$1**');
  const parts = normalized.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
  const runs = [];

  for (const part of parts) {
    const isBold = part.startsWith('**') && part.endsWith('**');
    const content = isBold ? part.slice(2, -2) : part;
    const cleaned = String(content || '')
      .replace(/\*(.*?)\*/g, '$1')
      .replace(/_(.*?)_/g, '$1')
      .replace(/\s+/g, ' ');
    if (!cleaned || cleaned.length === 0) {
      continue;
    }
    runs.push({ text: cleaned, bold: isBold });
  }

  if (runs.length === 0 && normalized.trim()) {
    runs.push({ text: normalized.trim(), bold: false });
  }

  return runs;
}

function parseMarkdownBlocks(markdownText) {
  const lines = String(markdownText || '').split(/\r?\n/);
  const blocks = [];
  let index = 0;

  while (index < lines.length) {
    const currentLine = lines[index].trim();
    if (!currentLine) {
      index += 1;
      continue;
    }

    if (/^[-*_]{3,}$/.test(currentLine)) {
      index += 1;
      continue;
    }

    const headingMatch = currentLine.match(/^(#{1,6})\s+(.*)$/);
    if (headingMatch) {
      blocks.push({ type: 'heading', level: headingMatch[1].length, text: cleanMarkdownInline(headingMatch[2].trim()) });
      index += 1;
      continue;
    }

    if (/^\d+\.\s+/.test(currentLine)) {
      const items = [];
      while (index < lines.length) {
        const listLine = (lines[index] || '').trim();
        if (!/^\d+\.\s+/.test(listLine)) {
          break;
        }
        items.push(cleanMarkdownKeepBold(listLine.replace(/^\d+\.\s+/, '')));
        index += 1;
      }
      blocks.push({ type: 'list', ordered: true, items });
      continue;
    }

    if (/^[-*+]\s+/.test(currentLine)) {
      const items = [];
      while (index < lines.length) {
        const listLine = (lines[index] || '').trim();
        if (!/^[-*+]\s+/.test(listLine)) {
          break;
        }
        items.push(cleanMarkdownKeepBold(listLine));
        index += 1;
      }
      blocks.push({ type: 'list', ordered: false, items });
      continue;
    }

    const nextLine = lines[index + 1] || '';
    if (currentLine.includes('|') && isMarkdownTableSeparator(nextLine)) {
      const headers = parseMarkdownTableRow(currentLine).map(cleanMarkdownInline);
      index += 2;
      const rows = [];
      while (index < lines.length) {
        const rowLine = (lines[index] || '').trim();
        if (!rowLine || !rowLine.includes('|')) {
          break;
        }
        rows.push(parseMarkdownTableRow(rowLine).map(cleanMarkdownInline));
        index += 1;
      }
      blocks.push({ type: 'table', headers, rows });
      continue;
    }

    const paragraphLines = [cleanMarkdownKeepBold(currentLine)];
    index += 1;
    while (index < lines.length) {
      const candidate = (lines[index] || '').trim();
      const candidateNext = lines[index + 1] || '';
      if (!candidate) {
        index += 1;
        break;
      }
      if (candidate.match(/^(#{1,6})\s+/)) {
        break;
      }
      if (/^\d+\.\s+/.test(candidate)) {
        break;
      }
      if (/^[-*+]\s+/.test(candidate)) {
        break;
      }
      if (candidate.includes('|') && isMarkdownTableSeparator(candidateNext)) {
        break;
      }
      paragraphLines.push(cleanMarkdownKeepBold(candidate));
      index += 1;
    }
    blocks.push({ type: 'paragraph', text: paragraphLines.filter(Boolean).join('\n') });
  }

  return blocks;
}

function SectionTable({ title, rows }) {
  if (!rows || rows.length === 0) {
    return null;
  }

  return (
    <div className="table-container" style={{ borderRadius: '12px' }}>
      <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--color-surface-hover)', fontWeight: 600 }}>
        {title}
      </div>
      <table>
        <thead>
          <tr>
            <th>SKU</th>
            <th>Product</th>
            <th>Risk</th>
            <th>DOS</th>
            <th>Shortfall</th>
            <th>Signal</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${title}-${row.sku_id}`}>
              <td>{row.sku_id}</td>
              <td>{row.product_name}</td>
              <td style={{ color: riskColor(row.risk_level), fontWeight: 600 }}>{row.risk_level}</td>
              <td>{row.days_of_supply?.toFixed ? row.days_of_supply.toFixed(1) : row.days_of_supply}</td>
              <td>{Number(row.demand_shortfall || 0).toLocaleString()}</td>
              <td>{row.signal_detail}</td>
              <td>{row.recommended_action}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function BuyerBrief() {
  const [metro, setMetro] = useState('Dallas');
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [requestMode, setRequestMode] = useState('preview');
  const [exportingPdf, setExportingPdf] = useState(false);
  const [error, setError] = useState('');
  const analyticsSectionRef = useRef(null);

  useEffect(() => {
    let cancelled = false;

    async function loadBrief({ forceRefresh = false, generateBrief = false } = {}) {
      if (!generateBrief) {
        setRequestMode('preview');
      }
      setLoading(true);
      try {
        const response = await fetchWeeklyBrief({ metro, forceRefresh, generateBrief });
        if (!cancelled) {
          setPayload(response);
          setError('');
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load buyer brief');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    // Load fast local preview on city change; do not consume Gemini by default.
    loadBrief({ forceRefresh: false, generateBrief: false });
    return () => {
      cancelled = true;
    };
  }, [metro]);

  const kpis = payload?.context?.kpis || {};
  const signalDrivers = payload?.context?.signal_drivers || [];
  const weekDate = payload?.brief_date || 'n/a';
  const sourceLabel =
    requestMode === 'generate'
      ? `Live generated (${payload?.provider || 'unknown provider'})`
      : 'Deterministic preview';

  const markdownText = payload?.brief_text || '';
  const urgentRows = payload?.context?.urgent_skus || [];
  const overstockRows = payload?.context?.overstock_skus || [];
  const watchRows = payload?.context?.watch_skus || [];
  const totalSkuCount = Number(payload?.context?.kpis?.total_skus || 0);
  const healthySkuCount = Math.max(totalSkuCount - urgentRows.length - overstockRows.length - watchRows.length, 0);

  const chartRows = useMemo(
    () => [
      ...urgentRows.map((row) => ({ ...row, bucket: 'Stockout Risk' })),
      ...overstockRows.map((row) => ({ ...row, bucket: 'Overstock Risk' })),
      ...watchRows.map((row) => ({ ...row, bucket: 'Watch' })),
    ],
    [urgentRows, overstockRows, watchRows],
  );

  const riskMixData = useMemo(
    () => [
      { name: 'Stockout risk', value: urgentRows.length, fill: 'var(--color-stockout-text)' },
      { name: 'Overstock risk', value: overstockRows.length, fill: 'var(--color-overstock-text)' },
      { name: 'Watch', value: watchRows.length, fill: 'var(--color-watch-text)' },
      { name: 'Healthy / OK', value: healthySkuCount, fill: 'rgba(148, 163, 184, 0.18)' },
    ],
    [urgentRows.length, overstockRows.length, watchRows.length, healthySkuCount],
  );

  const stockoutDriverData = useMemo(
    () =>
      [...urgentRows]
        .sort(
          (left, right) =>
            Number(right.lead_time_days || 0) / Math.max(Number(right.days_of_supply || 0), 1) -
            Number(left.lead_time_days || 0) / Math.max(Number(left.days_of_supply || 0), 1),
        )
        .slice(0, 6)
        .map((row) => ({
          sku: row.sku_id,
          shortfall: Number(row.demand_shortfall || 0),
          dos: Number(row.days_of_supply || 0),
          leadTime: Number(row.lead_time_days || 0),
          stressScore: Number(((Number(row.lead_time_days || 0) / Math.max(Number(row.days_of_supply || 0), 1)) * 100).toFixed(1)),
          signal: row.primary_signal,
          action: row.recommended_action,
        })),
    [urgentRows],
  );

  const overstockDriverData = useMemo(
    () =>
      [...overstockRows]
        .sort((left, right) => Number(right.days_of_supply || 0) - Number(left.days_of_supply || 0))
        .slice(0, 6)
        .map((row) => ({
          sku: row.sku_id,
          dos: Number(row.days_of_supply || 0),
          stock: Number(row.current_stock || 0),
          forecast: Number(row.forecast_demand_60d || 0),
          action: row.recommended_action,
        })),
    [overstockRows],
  );

  const signalReasonData = useMemo(() => {
    const counts = new Map();
    for (const row of chartRows) {
      const label = row.primary_signal || 'Unknown';
      counts.set(label, (counts.get(label) || 0) + 1);
    }
    return [...counts.entries()]
      .map(([name, value]) => ({ name, value }))
      .sort((left, right) => right.value - left.value)
      .slice(0, 6);
  }, [chartRows]);

  const postureScatterData = useMemo(
    () => ({
      stockout: urgentRows.map((row) => ({
        sku: row.sku_id,
        dos: Number(row.days_of_supply || 0),
        forecast: Number(row.forecast_demand_60d || 0),
        shortfall: Number(row.demand_shortfall || 0),
      })),
      overstock: overstockRows.map((row) => ({
        sku: row.sku_id,
        dos: Number(row.days_of_supply || 0),
        forecast: Number(row.forecast_demand_60d || 0),
        stock: Number(row.current_stock || 0),
      })),
      watch: watchRows.map((row) => ({
        sku: row.sku_id,
        dos: Number(row.days_of_supply || 0),
        forecast: Number(row.forecast_demand_60d || 0),
      })),
    }),
    [urgentRows, overstockRows, watchRows],
  );

  const totalFlagged = urgentRows.length + overstockRows.length + watchRows.length;
  const topStockout = stockoutDriverData[0];
  const topOverstock = overstockDriverData[0];
  const leadingSignal = signalReasonData[0];

  async function handleExportPdf() {
    if (!payload || exportingPdf) {
      return;
    }

    setExportingPdf(true);
    try {
      const pdf = new jsPDF('p', 'mm', 'a4');
      const pageWidth = pdf.internal.pageSize.getWidth();
      const margin = 14;
      const contentWidth = pageWidth - margin * 2;
      const bodyLineHeight = 4.6;
      const paragraphGap = 2.2;
      const listItemGap = 1.4;
      const blockGap = 3.0;

      const addHeader = () => {
        const currentPage = pdf.getCurrentPageInfo().pageNumber;
        pdf.setFont('helvetica', 'normal');
        pdf.setFontSize(9);
        pdf.setTextColor(110, 110, 110);
        pdf.text(`Buyer Dossier - ${payload?.context?.metro || metro}`, margin, 8);
        pdf.text(`Page ${currentPage}`, pageWidth - margin, 8, { align: 'right' });
      };

      const ensurePageBreak = (neededSpace, cursorY) => {
        if (cursorY + neededSpace > 285) {
          pdf.addPage();
          addHeader();
          return 18;
        }
        return cursorY;
      };

      const renderRichText = (runs, startX, startY, maxWidth, lineHeight = bodyLineHeight) => {
        let x = startX;
        let y = startY;

        for (const run of runs) {
          const tokens = run.text.split(/(\s+)/).filter((token) => token.length > 0);
          for (const token of tokens) {
            pdf.setFont('helvetica', run.bold ? 'bold' : 'normal');
            pdf.setFontSize(10.2);

            if (token.includes('\n')) {
              const parts = token.split('\n');
              for (let partIndex = 0; partIndex < parts.length; partIndex += 1) {
                const part = parts[partIndex];
                if (part) {
                  const partWidth = pdf.getTextWidth(part);
                  if (x + partWidth > startX + maxWidth) {
                    y = ensurePageBreak(lineHeight + 2, y + lineHeight);
                    x = startX;
                  }
                  if (!(part.trim() === '' && x === startX)) {
                    pdf.text(part, x, y);
                    x += partWidth;
                  }
                }
                if (partIndex < parts.length - 1) {
                  y = ensurePageBreak(lineHeight + 2, y + lineHeight);
                  x = startX;
                }
              }
              continue;
            }

            const tokenWidth = pdf.getTextWidth(token);

            if (x + tokenWidth > startX + maxWidth && token.trim()) {
              y = ensurePageBreak(lineHeight + 2, y + lineHeight);
              x = startX;
            }

            if (!token.trim() && x === startX) {
              continue;
            }

            pdf.text(token, x, y);
            x += tokenWidth;
          }
          if (x > startX + maxWidth - 4) {
            y = ensurePageBreak(lineHeight + 2, y + lineHeight);
            x = startX;
          }
        }

        return y + lineHeight;
      };

      const renderSkuTable = (title, rows, cursorYStart) => {
        let cursorY = ensurePageBreak(40, cursorYStart);
        pdf.setFont('helvetica', 'bold');
        pdf.setFontSize(12.5);
        pdf.setTextColor(20, 20, 20);
        pdf.text(title, margin, cursorY);

        const body = rows.length
          ? rows.map((row) => [
              row.sku_id,
              row.product_name,
              row.risk_level,
              String(Number(row.days_of_supply || 0).toFixed(1)),
              formatNumber(row.demand_shortfall),
              row.primary_signal || row.signal_detail || 'n/a',
              row.recommended_action || 'n/a',
            ])
          : [['-', 'No rows in this bucket', '-', '-', '-', '-', '-']];

        autoTable(pdf, {
          startY: cursorY + 2,
          margin: { left: margin, right: margin },
          head: [['SKU', 'Product', 'Risk', 'DOS', 'Shortfall', 'Signal', 'Action']],
          body,
          theme: 'striped',
          styles: { fontSize: 8.6, cellPadding: 2.2, overflow: 'linebreak' },
          headStyles: { fillColor: [38, 42, 52], textColor: [245, 245, 245] },
          columnStyles: {
            1: { cellWidth: 34 },
            5: { cellWidth: 26 },
            6: { cellWidth: 40 },
          },
        });
        return (pdf.lastAutoTable?.finalY || cursorY) + 6;
      };

      addHeader();
      let cursorY = 18;

      pdf.setFont('helvetica', 'bold');
      pdf.setFontSize(18);
      pdf.setTextColor(18, 18, 18);
      pdf.text('Weekly Buyer Brief Dossier', margin, cursorY);

      cursorY += 4;
      autoTable(pdf, {
        startY: cursorY,
        margin: { left: margin, right: margin },
        head: [['Field', 'Value']],
        body: [
          ['Metro', String(payload?.context?.metro || metro)],
          ['Distribution Center', String(payload?.context?.dc_name || 'n/a')],
          ['Brief Date', String(payload?.brief_date || 'n/a')],
          ['Provider', String(payload?.provider || 'n/a')],
          ['Generated At', String(payload?.generated_at ? new Date(payload.generated_at).toLocaleString() : 'n/a')],
          ['Cache Hit', payload?.cache_hit ? 'Yes' : 'No'],
        ],
        theme: 'grid',
        styles: { fontSize: 9, cellPadding: 2.0 },
        headStyles: { fillColor: [38, 42, 52], textColor: [245, 245, 245] },
        columnStyles: {
          0: { cellWidth: 42 },
          1: { cellWidth: contentWidth - 42 },
        },
      });

      cursorY = (pdf.lastAutoTable?.finalY || cursorY) + 7;
      pdf.setFont('helvetica', 'bold');
      pdf.setFontSize(13);
      pdf.setTextColor(20, 20, 20);
      pdf.text('Executive Summary', margin, cursorY);

      cursorY += 5;
      pdf.setFont('helvetica', 'normal');
      pdf.setFontSize(10.5);
      pdf.setTextColor(60, 60, 60);
      const summaryLines = pdf.splitTextToSize(payload?.context?.week_summary || 'No summary available.', contentWidth);
      pdf.text(summaryLines, margin, cursorY);
      cursorY += summaryLines.length * 4.4 + 2;

      cursorY = ensurePageBreak(28, cursorY);
      pdf.setFont('helvetica', 'bold');
      pdf.setFontSize(12.5);
      pdf.setTextColor(20, 20, 20);
      pdf.text('KPI Snapshot', margin, cursorY);

      autoTable(pdf, {
        startY: cursorY + 2,
        margin: { left: margin, right: margin },
        head: [['Metric', 'Value']],
        body: [
          ['Total SKUs', formatNumber(kpis.total_skus)],
          ['At-Risk Shortfall', formatNumber(kpis.at_risk_shortfall)],
          ['Average Days of Supply', String(kpis.avg_days_of_supply ?? 'n/a')],
          ['High Surge SKUs', formatNumber(kpis.high_surge_skus)],
          ['Healthy / OK SKUs', formatNumber(healthySkuCount)],
          ['Stockout Risk SKUs', String(urgentRows.length)],
          ['Overstock SKUs', String(overstockRows.length)],
          ['Watch SKUs', String(watchRows.length)],
          ['Net Shortfall Exposure (Units)', formatNumber(kpis.at_risk_shortfall)],
          ['Average DOS (Snapshot)', String(kpis.avg_days_of_supply ?? 'n/a')],
        ],
        theme: 'grid',
        headStyles: { fillColor: [28, 32, 40], textColor: [250, 250, 250] },
        styles: { fontSize: 10, cellPadding: 2.4 },
        columnStyles: {
          0: { cellWidth: 52 },
          1: { cellWidth: contentWidth - 52 },
        },
      });
      cursorY = (pdf.lastAutoTable?.finalY || cursorY) + 7;

      cursorY = renderSkuTable('Urgent Actions - Stockout Risk', urgentRows, cursorY);
      cursorY = renderSkuTable('Overstock Actions', overstockRows, cursorY);
      cursorY = renderSkuTable('Watch List', watchRows, cursorY);

      cursorY = ensurePageBreak(34, cursorY);
      pdf.setFont('helvetica', 'bold');
      pdf.setFontSize(12.5);
      pdf.setTextColor(20, 20, 20);
      pdf.text('Signal Diagnostics', margin, cursorY);

      autoTable(pdf, {
        startY: cursorY + 2,
        margin: { left: margin, right: margin },
        head: [['SKU', 'Date', 'Sales 7d %', 'Search 7d %', 'Permits 30d %', 'Holiday', 'Scenario', 'Surge']],
        body: (signalDrivers.length
          ? signalDrivers
          : [{ sku_id: '-', date: '-', sales_velocity_7d: '-', search_velocity_7d: '-', permit_velocity_30d: '-', holiday_factor: '-', scenario_type: '-', surge_score: '-' }]).map((row) => [
          row.sku_id,
          row.date,
          String(row.sales_velocity_7d),
          String(row.search_velocity_7d),
          String(row.permit_velocity_30d),
          String(row.holiday_factor),
          row.scenario_type,
          String(row.surge_score),
        ]),
        theme: 'grid',
        styles: { fontSize: 8.3, cellPadding: 2.0 },
        headStyles: { fillColor: [38, 42, 52], textColor: [245, 245, 245] },
      });
      cursorY = (pdf.lastAutoTable?.finalY || cursorY) + 7;

      if (analyticsSectionRef.current) {
        cursorY = ensurePageBreak(80, cursorY);
        pdf.setFont('helvetica', 'bold');
        pdf.setFontSize(12.5);
        pdf.setTextColor(20, 20, 20);
        pdf.text('Analytics Charts', margin, cursorY);

        const analyticsCards = Array.from(analyticsSectionRef.current.querySelectorAll('.metric-card'));
        const pageTop = 18;
        const pageBottom = 285;
        const colGap = 6;
        const rowGap = 6;
        const colWidth = (contentWidth - colGap) / 2;
        let flowY = cursorY + 3;

        const renderedCards = [];
        for (const card of analyticsCards) {
          const cardCanvas = await html2canvas(card, {
            scale: 2,
            useCORS: true,
            backgroundColor: '#ffffff',
            windowWidth: card.scrollWidth,
            windowHeight: card.scrollHeight,
            onclone: (clonedDoc) => {
              clonedDoc.documentElement.setAttribute('data-theme', 'light');
            },
          });
          const imageData = cardCanvas.toDataURL('image/png');
          const renderHeight = (cardCanvas.height * colWidth) / cardCanvas.width;
          renderedCards.push({ imageData, renderHeight });
        }

        for (let rowStart = 0; rowStart < renderedCards.length; rowStart += 2) {
          const rowCards = renderedCards.slice(rowStart, rowStart + 2);
          const rowHeight = Math.max(...rowCards.map((rowCard) => rowCard.renderHeight));

          if (flowY + rowHeight > pageBottom) {
            pdf.addPage();
            addHeader();
            flowY = pageTop;
          }

          for (let col = 0; col < rowCards.length; col += 1) {
            const rowCard = rowCards[col];
            const drawX = margin + col * (colWidth + colGap);
            pdf.addImage(rowCard.imageData, 'PNG', drawX, flowY, colWidth, rowCard.renderHeight);
          }

          flowY += rowHeight + rowGap;
        }

        cursorY = flowY;
      }

      pdf.addPage();
      addHeader();
      cursorY = 18;
      pdf.setFont('helvetica', 'bold');
      pdf.setFontSize(12.5);
      pdf.setTextColor(20, 20, 20);
      pdf.text('Narrative Dossier', margin, cursorY);

      cursorY += 4;
      const markdownBlocks = parseMarkdownBlocks(markdownText);
      for (const block of markdownBlocks) {
        if (block.type === 'heading') {
          const sectionMatch = block.text.match(/^(\d+)\.\s+/);
          const sectionNumber = sectionMatch ? Number(sectionMatch[1]) : null;
          if (sectionNumber === 3 || sectionNumber === 5 || sectionNumber === 7) {
            pdf.addPage();
            addHeader();
            cursorY = 18;
          }

          cursorY = ensurePageBreak(10, cursorY);
          pdf.setFont('helvetica', 'bold');
          pdf.setFontSize(11.5);
          pdf.setTextColor(30, 30, 30);
          pdf.text(block.text, margin, cursorY);
          cursorY += 6.5;
          continue;
        }

        if (block.type === 'table') {
          const headers = block.headers.filter(Boolean);
          const hasHeaders = headers.length > 0;
          const normalizedRows = (block.rows || []).map((row) => {
            const rowCells = [...row];
            if (hasHeaders && rowCells.length < headers.length) {
              while (rowCells.length < headers.length) {
                rowCells.push('');
              }
            }
            return hasHeaders ? rowCells.slice(0, headers.length) : rowCells;
          });

          autoTable(pdf, {
            startY: cursorY,
            margin: { left: margin, right: margin },
            head: hasHeaders ? [headers] : undefined,
            body: normalizedRows.length ? normalizedRows : [['No table rows']],
            theme: 'grid',
            styles: { fontSize: 8.6, cellPadding: 1.8, overflow: 'linebreak' },
            headStyles: { fillColor: [38, 42, 52], textColor: [245, 245, 245] },
          });
          cursorY = (pdf.lastAutoTable?.finalY || cursorY) + blockGap;
          continue;
        }

        if (block.type === 'paragraph') {
          pdf.setTextColor(55, 55, 55);
          const runs = parseInlineRuns(block.text);
          cursorY = ensurePageBreak(8, cursorY);
          cursorY = renderRichText(runs, margin, cursorY, contentWidth);
          cursorY += paragraphGap;
          continue;
        }

        if (block.type === 'list') {
          for (let itemIndex = 0; itemIndex < (block.items || []).length; itemIndex += 1) {
            const item = block.items[itemIndex];
            const listText = cleanMarkdownKeepBold(item);
            const runs = parseInlineRuns(listText);
            cursorY = ensurePageBreak(8, cursorY);
            pdf.setFont('helvetica', 'normal');
            pdf.setFontSize(10.2);
            pdf.setTextColor(55, 55, 55);
            const prefix = block.ordered ? `${itemIndex + 1}.` : '•';
            pdf.text(prefix, margin, cursorY);
            cursorY = renderRichText(runs, margin + 6, cursorY, contentWidth - 6);
            cursorY += listItemGap;
          }
          cursorY += blockGap;
        }
      }

      if (markdownBlocks.length === 0) {
        const lines = pdf.splitTextToSize('No narrative content available for this run.', contentWidth);
        pdf.text(lines, margin, cursorY);
      }

      const totalPages = pdf.getNumberOfPages();
      for (let page = 1; page <= totalPages; page += 1) {
        pdf.setPage(page);
        pdf.setFont('helvetica', 'normal');
        pdf.setFontSize(9);
        pdf.setTextColor(120, 120, 120);
        pdf.text(`${payload?.context?.metro || metro} Buyer Dossier`, margin, 292);
        pdf.text(`Page ${page}/${totalPages}`, pageWidth - margin, 292, { align: 'right' });
      }

      const metroLabel = (payload?.context?.metro || metro).replace(/\s+/g, '-').toLowerCase();
      const dateLabel = payload?.brief_date || new Date().toISOString().slice(0, 10);
      pdf.save(`buyer-dossier-${metroLabel}-${dateLabel}.pdf`);
    } catch {
      setError('Failed to export structured PDF brief');
    } finally {
      setExportingPdf(false);
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ fontSize: '2.2rem', marginBottom: '8px' }}>Buyer Weekly Brief</h1>
          <p style={{ color: 'var(--color-text-secondary)', margin: 0 }}>
            Distribution-center decision brief for week of {weekDate}
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button
            className="secondary-btn"
            disabled={exportingPdf || generating || loading || !payload}
            onClick={handleExportPdf}
          >
            {exportingPdf ? 'Exporting PDF...' : 'Export PDF'}
          </button>
          <select
            value={metro}
            onChange={(event) => setMetro(event.target.value)}
            style={{
              padding: '10px 12px',
              borderRadius: '8px',
              border: '1px solid var(--color-surface-hover)',
              background: 'var(--color-surface-floating)',
              color: 'var(--color-text-primary)',
              minWidth: '180px',
            }}
          >
            {METROS.map((city) => (
              <option key={city} value={city}>{city}</option>
            ))}
          </select>
          <button
            className="action-btn"
            disabled={generating}
            onClick={async () => {
              setRequestMode('generate');
              setGenerating(true);
              setLoading(true);
              try {
                const response = await fetchWeeklyBrief({ metro, forceRefresh: false, generateBrief: true });
                setPayload(response);
                setError('');
              } catch (err) {
                setError(err instanceof Error ? err.message : 'Failed to generate brief');
              } finally {
                setGenerating(false);
                setLoading(false);
              }
            }}
          >
            {generating ? 'Generating...' : 'Generate Brief'}
          </button>
        </div>
      </div>

      {generating ? (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(7, 12, 20, 0.62)',
            backdropFilter: 'blur(2px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 999,
            padding: '20px',
          }}
        >
          <div
            style={{
              width: 'min(560px, 100%)',
              background: 'var(--color-surface-floating)',
              border: '1px solid var(--color-surface-hover)',
              borderRadius: '16px',
              padding: '24px',
              boxShadow: '0 24px 60px rgba(0, 0, 0, 0.35)',
            }}
          >
            <div style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '8px' }}>
              Generating Weekly Brief
            </div>
            <div style={{ color: 'var(--color-text-secondary)', marginBottom: '12px' }}>
              Waiting for Gemini, with Ollama fallback if needed. This can take up to about 90 seconds.
            </div>
            <div style={{ color: 'var(--color-text-primary)', fontWeight: 600 }}>
              Processing request for {metro}...
            </div>
          </div>
        </div>
      ) : null}

      {error ? (
        <div className="metric-card" style={{ borderColor: 'var(--color-stockout-text)' }}>
          <div style={{ color: 'var(--color-stockout-text)', fontWeight: 600 }}>Error loading brief</div>
          <div style={{ color: 'var(--color-text-secondary)', marginTop: '8px' }}>{error}</div>
        </div>
      ) : null}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px' }}>
        <div className="metric-card">
          <div className="metric-title">Total SKUs</div>
          <div className="metric-value">{Number(kpis.total_skus || 0).toLocaleString()}</div>
        </div>
        <div className="metric-card">
          <div className="metric-title">At-Risk Shortfall</div>
          <div className="metric-value">{Number(kpis.at_risk_shortfall || 0).toLocaleString()}</div>
        </div>
        <div className="metric-card">
          <div className="metric-title">Avg Days of Supply</div>
          <div className="metric-value">{kpis.avg_days_of_supply ?? 'n/a'}</div>
        </div>
        <div className="metric-card">
          <div className="metric-title">High Surge SKUs</div>
          <div className="metric-value">{Number(kpis.high_surge_skus || 0).toLocaleString()}</div>
        </div>
      </div>

      <div className="metric-card">
        <div className="metric-header">
          <div className="metric-title">Weekly Summary ({payload?.context?.metro || metro} / {payload?.context?.dc_name || 'n/a'})</div>
          <div className="metric-trend">Provider: {payload?.provider || 'n/a'} {payload?.cache_hit ? '(cache)' : ''}</div>
        </div>
        <div style={{ color: 'var(--color-text-secondary)', marginBottom: '10px', fontSize: '0.85rem' }}>
          City changes load a deterministic preview. Click Generate Brief to run Gemini (with Ollama fallback).
        </div>
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            padding: '5px 10px',
            borderRadius: '999px',
            background: 'var(--color-surface-hover)',
            color: 'var(--color-text-primary)',
            fontSize: '0.8rem',
            marginBottom: '10px',
            fontWeight: 600,
          }}
        >
          Showing: {sourceLabel}
        </div>
        <div style={{ color: 'var(--color-text-primary)' }}>{payload?.context?.week_summary || (loading ? 'Loading summary...' : 'No summary available.')}</div>
      </div>

      <div ref={analyticsSectionRef} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '16px' }}>
        <div className="metric-card" style={{ minHeight: '420px' }}>
          <div className="metric-header">
            <div className="metric-title">Risk Mix</div>
            <div className="metric-trend">{totalFlagged} flagged SKUs / {totalSkuCount} total</div>
          </div>
          <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.85rem', marginBottom: '12px' }}>
            A quick read on whether the DC is mostly fighting stockouts, overstock, watchlist pressure, or just healthy inventory.
          </div>
          {totalFlagged > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Tooltip
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: 'var(--shadow-diffused)', backgroundColor: 'var(--color-surface-floating)' }}
                />
                <Pie data={riskMixData} dataKey="value" nameKey="name" innerRadius={70} outerRadius={100} paddingAngle={2}>
                  {riskMixData.map((entry) => (
                    <Cell key={entry.name} fill={entry.fill} stroke={entry.name === 'Healthy / OK' ? 'rgba(148, 163, 184, 0.22)' : 'none'} />
                  ))}
                </Pie>
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChartState message="No flagged SKUs to chart yet." />
          )}
          {sectionInsight(
            'Buyer read',
            totalFlagged > 0
              ? `Risk is currently concentrated in ${totalFlagged} flagged SKUs while ${healthySkuCount} SKUs remain in a healthy posture. Stockout and overstock buckets should be handled separately because the mitigation play is different for each.`
              : `No flagged SKUs are present in this metro preview, so all ${healthySkuCount} SKUs are sitting in a healthy posture and the DC is currently in a low-alert state.`,
          )}
        </div>

        <div className="metric-card" style={{ minHeight: '420px' }}>
          <div className="metric-header">
            <div className="metric-title">Stockout Pressure</div>
            <div className="metric-trend">Lead-time pressure vs current coverage</div>
          </div>
          <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.85rem', marginBottom: '12px' }}>
            Sorted by replenishment stress score so buyers can see where lead time is most dangerous relative to days of supply.
          </div>
          {stockoutDriverData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={stockoutDriverData} margin={{ top: 10, right: 10, left: 0, bottom: 30 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(0,0,0,0.05)" />
                <XAxis dataKey="sku" tick={{ fill: 'var(--color-text-secondary)', fontSize: 11 }} axisLine={false} tickLine={false} interval={0} angle={-18} textAnchor="end" />
                <YAxis tick={{ fill: 'var(--color-text-secondary)', fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: 'var(--shadow-diffused)', backgroundColor: 'var(--color-surface-floating)' }}
                  formatter={(value, name) => {
                    if (name === 'stressScore') return [value, 'Stress score'];
                    if (name === 'leadTime') return [`${value} days`, 'Lead time'];
                    if (name === 'dos') return [`${value} days`, 'Days of supply'];
                    return [value, name];
                  }}
                />
                <Bar dataKey="stressScore" fill="var(--color-stockout-text)" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChartState message="No stockout-risk SKUs in this metro right now." />
          )}
          {sectionInsight(
            'Why it is at risk',
            topStockout
              ? `${topStockout.sku} has the highest replenishment stress score (${topStockout.stressScore}) with ${topStockout.leadTime} days of lead time and ${Number(topStockout.dos || 0).toFixed(1)} days of supply.`
              : 'There are no stockout-risk rows in the current brief, so the buyer should not allocate urgent replenishment capital here.',
          )}
        </div>

        <div className="metric-card" style={{ minHeight: '420px' }}>
          <div className="metric-header">
            <div className="metric-title">Overstock Pressure</div>
            <div className="metric-trend">What is tying up inventory</div>
          </div>
          <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.85rem', marginBottom: '12px' }}>
            High days-of-supply items are the clearest markdown, transfer, or cancellation candidates.
          </div>
          {overstockDriverData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={overstockDriverData} margin={{ top: 10, right: 10, left: 0, bottom: 30 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(0,0,0,0.05)" />
                <XAxis dataKey="sku" tick={{ fill: 'var(--color-text-secondary)', fontSize: 11 }} axisLine={false} tickLine={false} interval={0} angle={-18} textAnchor="end" />
                <YAxis tick={{ fill: 'var(--color-text-secondary)', fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: 'var(--shadow-diffused)', backgroundColor: 'var(--color-surface-floating)' }}
                  formatter={(value, name) => [formatNumber(value), name]}
                />
                <Bar dataKey="dos" fill="var(--color-overstock-text)" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChartState message="No overstock-risk SKUs in this metro right now." />
          )}
          {sectionInsight(
            'Why it is overstocked',
            topOverstock
              ? `${topOverstock.sku} is sitting at ${Number(topOverstock.dos || 0).toFixed(1)} days of supply, which is usually a demand-velocity problem rather than a replenishment problem.`
              : 'There are no overstock-risk rows in the current brief, so working capital pressure is lower here.',
          )}
        </div>

        <div className="metric-card" style={{ minHeight: '420px' }}>
          <div className="metric-header">
            <div className="metric-title">Signal Reasons</div>
            <div className="metric-trend">Why the model is flagging items</div>
          </div>
          <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.85rem', marginBottom: '12px' }}>
            This groups the primary signal labels behind the flagged SKUs so the buyer can see the causal pattern.
          </div>
          {signalReasonData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={signalReasonData} layout="vertical" margin={{ top: 10, right: 20, left: 20, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="rgba(0,0,0,0.05)" />
                <XAxis type="number" tick={{ fill: 'var(--color-text-secondary)', fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="name" tick={{ fill: 'var(--color-text-secondary)', fontSize: 11 }} axisLine={false} tickLine={false} width={120} />
                <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: 'var(--shadow-diffused)', backgroundColor: 'var(--color-surface-floating)' }} />
                <Bar dataKey="value" fill="var(--color-watch-text)" radius={[0, 8, 8, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChartState message="No signal reason data yet." />
          )}
          {sectionInsight(
            'Primary signal',
            leadingSignal
              ? `${leadingSignal.name} is the dominant driver across current flagged SKUs, so the buying response should focus on the signal type rather than treating all SKUs the same.`
              : 'The brief has no active signal clusters yet, so there is no dominant causal pattern to highlight.',
          )}
        </div>

        <div className="metric-card" style={{ minHeight: '420px' }}>
          <div className="metric-header">
            <div className="metric-title">Inventory Posture Scatter</div>
            <div className="metric-trend">Days of supply vs 60-day forecast</div>
          </div>
          <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.85rem', marginBottom: '12px' }}>
            Low days-of-supply with high forecast points to stockout risk; high days-of-supply with soft forecast points to overstock.
          </div>
          {chartRows.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <ScatterChart margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(0,0,0,0.05)" />
                <XAxis type="number" dataKey="dos" name="Days of supply" tick={{ fill: 'var(--color-text-secondary)', fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis type="number" dataKey="forecast" name="Forecast 60d" tick={{ fill: 'var(--color-text-secondary)', fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: 'var(--shadow-diffused)', backgroundColor: 'var(--color-surface-floating)' }}
                  formatter={(value, name) => [formatNumber(value), name]}
                />
                <Legend />
                <Scatter name="Stockout risk" data={postureScatterData.stockout} fill="var(--color-stockout-text)" />
                <Scatter name="Overstock risk" data={postureScatterData.overstock} fill="var(--color-overstock-text)" />
                <Scatter name="Watch" data={postureScatterData.watch} fill="var(--color-watch-text)" />
                <Scatter name="Healthy / OK" data={[]} fill="rgba(148, 163, 184, 0.18)" />
              </ScatterChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChartState message="No inventory posture data to plot yet." />
          )}
          {sectionInsight(
            'What the scatter tells the buyer',
            'Points in the bottom-left need replenishment attention, while points in the top-right need markdown or transfer attention. This gives the buyer a fast way to separate service-level risk from working-capital risk.',
          )}
        </div>
      </div>

      <SectionTable title="Urgent Actions (Stockout Risk)" rows={payload?.context?.urgent_skus || []} />
      <SectionTable title="Overstock Actions" rows={payload?.context?.overstock_skus || []} />
      <SectionTable title="Watch List" rows={payload?.context?.watch_skus || []} />

      <div className="table-container" style={{ borderRadius: '12px' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--color-surface-hover)', fontWeight: 600 }}>
          Signal Diagnostics
        </div>
        <table>
          <thead>
            <tr>
              <th>SKU</th>
              <th>Date</th>
              <th>Sales 7d %</th>
              <th>Search 7d %</th>
              <th>Permits 30d %</th>
              <th>Holiday Factor</th>
              <th>Scenario</th>
              <th>Surge</th>
            </tr>
          </thead>
          <tbody>
            {signalDrivers.map((row) => (
              <tr key={`driver-${row.sku_id}-${row.date}`}>
                <td>{row.sku_id}</td>
                <td>{row.date}</td>
                <td>{row.sales_velocity_7d}</td>
                <td>{row.search_velocity_7d}</td>
                <td>{row.permit_velocity_30d}</td>
                <td>{row.holiday_factor}</td>
                <td>{row.scenario_type}</td>
                <td>{row.surge_score}</td>
              </tr>
            ))}
            {signalDrivers.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ color: 'var(--color-text-secondary)' }}>
                  {loading ? 'Loading diagnostics...' : 'No signal diagnostics available.'}
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <div className="metric-card" style={{ fontFamily: 'var(--font-sans)', lineHeight: 1.6 }}>
        <div className="metric-header">
          <div className="metric-title">Comprehensive Plain-Language Brief</div>
        </div>
        {loading && !payload ? (
          <div style={{ color: 'var(--color-text-secondary)' }}>Loading brief...</div>
        ) : (
          <div className="brief-markdown">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {markdownText}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
