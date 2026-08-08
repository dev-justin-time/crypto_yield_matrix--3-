// Crypto underlying asset cash-yield matrix
// Loads the enriched CSV and renders the quarterly comparison infographic.

(function () {
  'use strict';

  const QUARTERS = [
    { key: 'q3_24_prior', label: "Q3 '24", window: 'prior' },
    { key: 'q4_24_prior', label: "Q4 '24", window: 'prior' },
    { key: 'q1_25_prior', label: "Q1 '25", window: 'prior' },
    { key: 'q2_25_prior', label: "Q2 '25", window: 'prior' },
    { key: 'q3_25_current', label: "Q3 '25", window: 'current' },
    { key: 'q4_25_current', label: "Q4 '25", window: 'current' },
    { key: 'q1_26_current', label: "Q1 '26", window: 'current' },
    { key: 'q2_26_current', label: "Q2 '26", window: 'current' }
  ];

  const LIGHT_BLOCKS = new Set(['SOL', 'SUI', 'APT', 'CELO', 'FLOW', 'GLMR', 'MINA', 'MNDE', 'PENDLE', 'HYPE', 'ONDO']);
  const FOCUS_SYMBOLS = ['BTC', 'ETH', 'SOL', 'MATIC', 'ADA', 'XRP'];
  const ASSET_CATALOG_URL = 'asset_catalog.csv';
  const LIVE_SNAPSHOT_URL = 'live_data/live_snapshot.json';
  const SOURCE_COVERAGE_LABELS = { source_snapshot: 'source snapshot', canonical_only: 'canonical yield only' };
  let tooltipId = 0;
  const CATEGORY_LABELS = {
    ai: 'AI',
    defi: 'DeFi',
    depin: 'DePIN',
    enterprise: 'Enterprise',
    infrastructure: 'Infrastructure',
    layer1: 'Layer 1',
    layer2: 'Layer 2',
    media: 'Media',
    nft: 'NFT',
    oracle: 'Oracle',
    other: 'Other',
    payments: 'Payments',
    privacy: 'Privacy',
    rwa: 'RWA',
    storage: 'Storage',
    store_of_value: 'Store of value'
  };

  function parseCSV(text) {
    const rows = [];
    let row = [];
    let cell = '';
    let quoted = false;

    for (let i = 0; i < text.length; i += 1) {
      const char = text[i];
      const next = text[i + 1];
      if (char === '"' && quoted && next === '"') {
        cell += '"';
        i += 1;
      } else if (char === '"') {
        quoted = !quoted;
      } else if (char === ',' && !quoted) {
        row.push(cell.trim());
        cell = '';
      } else if ((char === '\n' || char === '\r') && !quoted) {
        if (char === '\r' && next === '\n') i += 1;
        row.push(cell.trim());
        if (row.some(value => value !== '')) rows.push(row);
        row = [];
        cell = '';
      } else {
        cell += char;
      }
    }
    if (cell || row.length) {
      row.push(cell.trim());
      if (row.some(value => value !== '')) rows.push(row);
    }

    const headers = (rows.shift() || []).map(header => header.replace(/^"|"$/g, ''));
    return rows.map(values => headers.reduce((asset, header, index) => {
      asset[header] = (values[index] || '').replace(/^"|"$/g, '');
      return asset;
    }, {}));
  }

  function number(value, fallback = 0) {
    const parsed = Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function average(assets, key) {
    return assets.length ? assets.reduce((sum, asset) => sum + number(asset[key]), 0) / assets.length : 0;
  }

  function formatNumber(value, digits = 2) {
    return number(value).toLocaleString('en-US', {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits
    });
  }

  function formatUsd(value) {
    const amount = number(value);
    if (amount >= 1e12) return `$${(amount / 1e12).toFixed(2)}T`;
    if (amount >= 1e9) return `$${(amount / 1e9).toFixed(1)}B`;
    if (amount >= 1e6) return `$${(amount / 1e6).toFixed(1)}M`;
    return `$${formatNumber(amount, 0)}`;
  }

  function text(element, value) {
    element.textContent = value == null ? '' : String(value);
    return element;
  }

  function element(tag, className, value) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value !== undefined) text(node, value);
    return node;
  }

  function validColor(color) {
    return /^#[0-9a-f]{6}$/i.test(color || '') ? color : '#64748b';
  }

  function signed(value, digits = 2) {
    const amount = number(value);
    return `${amount > 0 ? '+' : ''}${amount.toFixed(digits)}`;
  }

  function changeClass(value) {
    const amount = number(value);
    if (amount > 0.05) return 'change-up';
    if (amount < -0.05) return 'change-down';
    return 'change-flat';
  }

  function coverageLabel(asset) {
    return SOURCE_COVERAGE_LABELS[asset.snapshot_status] || 'coverage unavailable';
  }

  function buildExplorer(assets, catalog, liveSnapshot) {
    const grid = document.getElementById('asset-catalog-grid');
    const insights = document.getElementById('asset-insights');
    const search = document.getElementById('asset-search');
    const category = document.getElementById('category-filter');
    const coverage = document.getElementById('coverage-filter');
    const quote = document.getElementById('quote-filter');
    const sort = document.getElementById('asset-sort');
    const download = document.getElementById('download-catalog');
    const downloadQuotes = document.getElementById('download-quotes');
    if (!grid || !insights || !search || !category || !coverage || !quote || !sort) return;

    const categories = [...new Set(catalog.map(asset => asset.category).filter(Boolean))].sort();
    categories.forEach(value => {
      const option = element('option', '', CATEGORY_LABELS[value] || value);
      option.value = value;
      category.append(option);
    });
    const render = () => {
      const query = search.value.trim().toLowerCase();
      const filtered = catalog.filter(asset => {
        const matchesQuery = !query || `${asset.symbol} ${asset.name} ${asset.category}`.toLowerCase().includes(query);
        return matchesQuery && (!category.value || asset.category === category.value) && (!coverage.value || asset.snapshot_status === coverage.value) && (!quote.value || asset.quote_status === quote.value);
      });
      const sorters = {
        yield: (asset) => number(asset.agg_current),
        change: (asset) => number(asset.change_pp),
        score: (asset) => number(asset.investment_score),
        market_cap: (asset) => number(asset.snapshot_market_cap_usd || asset.mcap_end_current_usd)
      };
      const score = sorters[sort.value] || sorters.yield;
      filtered.sort((left, right) => score(right) - score(left) || left.symbol.localeCompare(right.symbol));
      grid.replaceChildren();
      filtered.slice(0, 60).forEach(asset => {
        const card = element('article', 'catalog-card');
        const title = element('div', 'catalog-card-title');
        title.append(element('span', 'catalog-symbol', asset.symbol), element('span', 'coverage-badge', coverageLabel(asset)));
        card.append(title);
        card.append(element('div', 'catalog-name', asset.name));
        const values = element('div', 'catalog-values');
        values.append(
          element('span', '', `${formatNumber(asset.agg_current)}% yield`),
          element('span', '', `${signed(asset.change_pp)}pp change`),
          element('span', '', `score ${formatNumber(asset.investment_score, 0)}`),
          element('span', '', asset.quote_status === 'source_snapshot' ? `${formatUsd(asset.snapshot_market_cap_usd)} mcap` : 'quote unavailable')
        );
        card.append(values);
        const note = asset.quote_status === 'source_snapshot'
          ? `Quote snapshot ${formatUsd(asset.snapshot_price_usd)} · ${signed(asset.snapshot_change_pct)}% latest change · ${asset.quote_as_of_iso || 'time unavailable'}`
          : 'Yield matrix coverage only. Obtain a current market quote before acting; no snapshot was supplied for this asset.';
        card.append(element('p', 'catalog-note', note));
        const liveAsset = liveSnapshot && liveSnapshot.market && liveSnapshot.market.assets
          ? liveSnapshot.market.assets[asset.symbol]
          : null;
        const generatedAt = liveSnapshot && liveSnapshot.generated_at ? new Date(liveSnapshot.generated_at) : null;
        const staleAfterMs = Number(liveSnapshot && liveSnapshot.freshness && liveSnapshot.freshness.stale_after_seconds || 900) * 1000;
        const snapshotFresh = generatedAt && Number.isFinite(generatedAt.getTime()) && Date.now() - generatedAt.getTime() >= 0 && Date.now() - generatedAt.getTime() <= staleAfterMs;
        const observedAt = liveAsset && liveAsset.observed_at ? new Date(liveAsset.observed_at) : null;
        const assetFresh = observedAt && Number.isFinite(observedAt.getTime()) && Date.now() - observedAt.getTime() >= 0 && Date.now() - observedAt.getTime() <= staleAfterMs;
        const usableLiveAsset = liveAsset && liveAsset.price_usd != null && liveAsset.observation_status !== 'retained_from_previous_cycle' && snapshotFresh && assetFresh && liveSnapshot.data_status === 'live_overlay_only';
        if (usableLiveAsset) {
          card.append(element('div', 'catalog-live', `Live overlay · ${formatUsd(liveAsset.price_usd)} · ${signed(liveAsset.change_24h_pct)}% 24h · ${liveAsset.provider_coverage || liveAsset.provider || 'provider'} · ${liveAsset.observed_at || 'time unavailable'}`));
        } else if (liveAsset && liveAsset.price_usd != null) {
          card.append(element('div', 'catalog-live stale', 'Live value retained but stale/degraded; do not treat it as current.'));
        } else {
          card.append(element('div', 'catalog-live unavailable', 'Live overlay unavailable for this asset; historical evidence remains unchanged.'));
        }
        card.append(element('div', 'catalog-cta', asset.quote_status === 'source_snapshot' ? 'Inspect quote + yield evidence →' : 'Explore yield evidence →'));
        grid.append(card);
      });
      const sourceCount = catalog.filter(asset => asset.snapshot_status === 'source_snapshot').length;
      const quoteCount = catalog.filter(asset => asset.quote_status === 'source_snapshot').length;
      const liveCount = liveSnapshot && liveSnapshot.market ? Number(liveSnapshot.market.asset_count || 0) : 0;
      insights.textContent = `${filtered.length} assets shown · ${quoteCount} quote exports available · ${liveCount} live market observations · ${sourceCount} source-backed yield snapshots · ${catalog.length - sourceCount} canonical-only rows · derived features are research aids, not forecasts.`;
    };
    [search, category, coverage, quote, sort].forEach(control => control.addEventListener('input', render));
    const filteredCatalog = () => {
      const query = search.value.trim().toLowerCase();
      return catalog.filter(asset => {
        const matchesQuery = !query || `${asset.symbol} ${asset.name} ${asset.category}`.toLowerCase().includes(query);
        return matchesQuery && (!category.value || asset.category === category.value) && (!coverage.value || asset.snapshot_status === coverage.value) && (!quote.value || asset.quote_status === quote.value);
      });
    };
    const downloadCsv = (rows, filename) => {
      const headers = Object.keys(rows[0] || {});
      const csv = [headers, ...rows.map(row => headers.map(header => row[header] || ''))]
        .map(row => row.map(value => `"${String(value).replace(/"/g, '""')}"`).join(','))
        .join('\\n');
      const link = document.createElement('a');
      link.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
      link.download = filename;
      link.click();
      URL.revokeObjectURL(link.href);
    };
    if (download) download.addEventListener('click', () => downloadCsv(filteredCatalog(), 'crypto-yield-matrix-shortlist.csv'));
    if (downloadQuotes) downloadQuotes.addEventListener('click', async () => {
      const rows = [];
      for (const asset of filteredCatalog()) {
        try {
          const response = await fetch(`csv/quotes/${encodeURIComponent(asset.symbol)}.csv`);
          if (response.ok) rows.push(...parseCSV(await response.text()));
        } catch (error) {
          console.warn(`quote export unavailable for ${asset.symbol}`, error);
        }
      }
      if (rows.length) downloadCsv(rows, 'crypto-yield-matrix-quote-exports.csv');
    });
    render();
  }

  function createAssetTooltip(asset, yieldValue, quarterLabel) {
    const tooltip = element('div', 'asset-tooltip');
    tooltip.setAttribute('role', 'tooltip');
    tooltip.setAttribute('aria-hidden', 'true');
    const heading = element('strong', 'tooltip-heading', `${asset.name} (${asset.symbol})`);
    const yieldLine = element('div', 'tooltip-yield', `${quarterLabel} · ${formatNumber(yieldValue)}% annualized yield`);
    const note = element('p', 'tooltip-note', asset.notes || 'No asset-specific methodology note supplied.');
    const details = element('div', 'tooltip-details');
    [
      ['category', CATEGORY_LABELS[asset.category] || asset.category || 'Unclassified'],
      ['current 12-mo', `${formatNumber(asset.agg_current)}%`],
      ['current market cap', formatUsd(asset.mcap_end_current_usd)],
      ['risk-adjusted yield', `${formatNumber(asset.risk_adjusted_yield)}%`],
      ['investment score', `${formatNumber(asset.investment_score, 0)}/100`],
      ['source coverage', coverageLabel(asset)],
      ['snapshot price', asset.snapshot_price_usd ? formatUsd(asset.snapshot_price_usd) : 'not supplied'],
      ['quote coverage', asset.quote_status === 'source_snapshot' ? `${asset.quote_completeness_pct || 0}% fields supplied` : 'unavailable'],
      ['quote export', asset.quote_file || 'not generated']
    ].forEach(([label, value]) => {
      const line = element('div', 'tooltip-detail');
      line.append(text(element('span', 'tooltip-label'), label));
      line.append(text(element('span', 'tooltip-value'), value));
      details.append(line);
    });
    tooltip.append(heading, yieldLine, note, details);
    if (asset.is_annualized === '1') {
      tooltip.append(element('div', 'tooltip-asterisk', '* annualized or newly listed category; compare with methodology notes'));
    }
    return tooltip;
  }

  function createAssetBlock(asset, yieldValue, quarterLabel, aggregate = false) {
    const block = element('button', aggregate ? 'agg-block' : 'asset-block');
    block.type = 'button';
    const assetColor = validColor(asset.color);
    block.style.setProperty('--asset-color', assetColor);
    // The original renderer painted each yield block directly. Keep that
    // behavior here instead of relying on a CSS variable that older themes
    // may not consume.
    if (!aggregate) block.style.backgroundColor = assetColor;
    tooltipId += 1;
    block.classList.toggle('block-light', LIGHT_BLOCKS.has(asset.symbol));
    block.setAttribute('aria-label', `${asset.name}, ${quarterLabel}, ${formatNumber(yieldValue)} percent annualized yield`);

    const left = element('span', 'asset-left');
    const icon = element('span', 'asset-icon', asset.icon || asset.symbol.slice(0, 1));
    icon.style.backgroundColor = aggregate ? assetColor : 'rgba(0, 0, 0, 0.25)';
    icon.setAttribute('aria-hidden', 'true');
    const name = element('span', 'asset-name', asset.name);
    left.append(icon, name);

    const value = element('span', 'asset-yield', `${formatNumber(yieldValue)}%`);
    if (asset.is_annualized === '1') value.append(element('sup', 'asterisk', '*'));
    block.append(left, value);

    if (!aggregate) {
      const tooltip = createAssetTooltip(asset, yieldValue, quarterLabel);
      tooltip.id = `asset-tooltip-${tooltipId}`;
      block.setAttribute('aria-describedby', tooltip.id);
      block.addEventListener('focus', () => tooltip.setAttribute('aria-hidden', 'false'));
      block.addEventListener('blur', () => tooltip.setAttribute('aria-hidden', 'true'));
      block.append(tooltip);
    }
    return block;
  }

  function createAggregateBlock(asset, current = false) {
    const value = current ? asset.agg_current : asset.agg_prior;
    const block = createAssetBlock(asset, value, current ? 'current 12-month aggregate' : 'prior 12-month aggregate', true);
    if (current) {
      const change = element('span', `agg-change ${changeClass(asset.change_pp)}`);
      const amount = number(asset.change_pp);
      text(change, `${amount > 0 ? '↑' : amount < 0 ? '↓' : '→'} ${signed(amount)}pp`);
      change.setAttribute('aria-label', `${signed(amount)} percentage point change versus prior window`);
      block.querySelector('.asset-yield').after(change);
    }
    return block;
  }

  function addHeader(grid, label, column, className, sublabel) {
    const header = element('div', `quarter-label ${className || ''}`);
    header.style.gridColumn = String(column);
    header.style.gridRow = '1';
    header.append(text(element('span', 'quarter-name'), label));
    if (sublabel) header.append(text(element('span', 'quarter-sublabel'), sublabel));
    grid.append(header);
  }

  function addStack(grid, assets, quarter, column) {
    const stack = element('div', 'stack-col');
    stack.style.gridColumn = String(column);
    stack.style.gridRow = '2';
    [...assets]
      .sort((a, b) => number(b[quarter.key]) - number(a[quarter.key]) || number(b.mcap_end_current_usd) - number(a.mcap_end_current_usd))
      .forEach(asset => stack.append(createAssetBlock(asset, number(asset[quarter.key]), quarter.label)));
    grid.append(stack);
  }

  function addAggregate(grid, assets, current, column) {
    const stack = element('div', `agg-col${current ? ' aggregate-current' : ''}`);
    stack.style.gridColumn = String(column);
    stack.style.gridRow = '2';
    [...assets]
      .sort((a, b) => number(b[current ? 'agg_current' : 'agg_prior']) - number(a[current ? 'agg_current' : 'agg_prior']))
      .forEach(asset => stack.append(createAggregateBlock(asset, current)));
    grid.append(stack);
  }

  function buildMatrix(assets) {
    const grid = document.getElementById('matrix-grid');
    if (!grid) return;
    grid.replaceChildren();

    const performance = element('div', 'perf-label');
    performance.style.gridColumn = '1';
    performance.style.gridRow = '1 / 3';
    const arrow = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    arrow.setAttribute('class', 'perf-arrow');
    arrow.setAttribute('viewBox', '0 0 24 24');
    arrow.setAttribute('aria-hidden', 'true');
    arrow.innerHTML = '<path d="M12 5v14M5 12l7 7 7-7" />';
    performance.append(arrow, element('span', '', 'performance'));
    grid.append(performance);

    QUARTERS.forEach((quarter, index) => {
      const column = index < 4 ? index + 2 : index + 3;
      addHeader(grid, quarter.label, column, quarter.window, index === 0 ? 'prior window' : index === 4 ? 'current window' : '');
    });

    const divider = element('div', 'divider-rule');
    divider.style.gridColumn = '6';
    divider.style.gridRow = '1 / 3';
    grid.append(divider);

    addHeader(grid, '12-month aggregate', 11, 'aggregate-header', 'prior');
    addHeader(grid, '12-month aggregate', 12, 'aggregate-header', 'current · change');

    QUARTERS.forEach((quarter, index) => addStack(grid, assets, quarter, index < 4 ? index + 2 : index + 3));
    addAggregate(grid, assets, false, 11);
    addAggregate(grid, assets, true, 12);
  }

  function buildLegend(assets) {
    const legend = document.getElementById('legend-row');
    if (!legend) return;
    legend.replaceChildren();
    legend.append(element('div', 'legend-heading', 'common yield ranges'));

    [
      ['low', '0–2%', 'capital preservation / lending equivalent'],
      ['core', '2–5%', 'mainstream staking and protocol rewards'],
      ['elevated', '5–10%', 'higher reward or inflation exposure'],
      ['high', '10%+', 'specialized or high-emission rewards']
    ].forEach(([className, range, label]) => {
      const item = element('div', `yield-band ${className}`);
      item.append(element('span', 'yield-band-range', range), element('span', 'yield-band-label', label));
      legend.append(item);
    });

    const categoryValues = new Map();
    assets.forEach(asset => {
      const key = asset.category || 'other';
      if (!categoryValues.has(key)) categoryValues.set(key, []);
      categoryValues.get(key).push(number(asset.agg_current));
    });
    const categoryRow = element('div', 'category-legend');
    [...categoryValues.entries()].sort((a, b) => a[0].localeCompare(b[0])).forEach(([category, values]) => {
      const representative = assets.find(asset => asset.category === category);
      const item = element('span', 'category-item');
      item.append(
        element('span', 'legend-dot', ''),
        text(element('span', 'category-name'), CATEGORY_LABELS[category] || category),
        text(element('span', 'category-range'), `${Math.min(...values).toFixed(1)}–${Math.max(...values).toFixed(1)}%`)
      );
      item.querySelector('.legend-dot').style.background = validColor(representative && representative.color);
      categoryRow.append(item);
    });
    legend.append(categoryRow);
  }

  function buildTimeline(assets, focusAssets) {
    const metrics = document.getElementById('timeline-metrics');
    if (!metrics) return;
    const prior = average(focusAssets, 'agg_prior');
    const current = average(focusAssets, 'agg_current');
    const firstQuarter = average(focusAssets, 'q3_24_prior');
    const latestQuarter = average(focusAssets, 'q2_26_current');
    const forecast = average(focusAssets, 'q3_26_forward_yield');
    const currentMarketCap = assets.reduce((sum, asset) => sum + number(asset.mcap_end_current_usd), 0);
    const currentTvl = assets.reduce((sum, asset) => sum + number(asset.tvl_usd), 0);
    const positiveChanges = assets.filter(asset => number(asset.change_pp) > 0.05).length;
    const annualized = assets.filter(asset => asset.is_annualized === '1').length;

    metrics.replaceChildren();
    [
      [focusAssets.length, 'focus assets shown'],
      [assets.length, 'assets in dataset'],
      ["8", 'quarters analyzed'],
      [`${formatNumber(firstQuarter)}%`, 'first quarter avg yield'],
      [`${formatNumber(latestQuarter)}%`, 'latest quarter avg yield'],
      [`${signed(current - prior)}pp`, '12-month avg change'],
      [formatUsd(currentMarketCap), 'current market cap tracked'],
      [formatUsd(currentTvl), 'TVL represented'],
      [`${formatNumber(forecast)}%`, 'next-quarter forecast avg'],
      [`${positiveChanges}/${assets.length}`, 'assets with positive change']
    ].forEach(([value, label]) => {
      const metric = element('div', 't-metric');
      metric.append(text(element('span', 't-metric-val'), value), text(element('span', 't-metric-lbl'), label));
      metrics.append(metric);
    });

    const title = document.querySelector('.timeline-title');
    if (title) title.textContent = `key data metrics · ${annualized} annualized categories · yield means use the six focus assets shown`;
  }

  async function init() {
    const grid = document.getElementById('matrix-grid');
    try {
      const liveStatus = document.getElementById('live-feed-status');
      const [yieldResponse, catalogResponse, liveResponse] = await Promise.all([
        fetch('yield_data.csv'),
        fetch(ASSET_CATALOG_URL),
        fetch(LIVE_SNAPSHOT_URL)
      ]);
      if (!yieldResponse.ok) throw new Error(`yield CSV request failed (${yieldResponse.status})`);
      if (!catalogResponse.ok) throw new Error(`asset catalog request failed (${catalogResponse.status})`);
      const assets = parseCSV(await yieldResponse.text()).filter(asset => asset.symbol && asset.name);
      const catalog = parseCSV(await catalogResponse.text()).filter(asset => asset.symbol && asset.name);
      let liveSnapshot = null;
      if (liveResponse.ok) {
        try { liveSnapshot = await liveResponse.json(); } catch (error) { console.warn('live overlay JSON is invalid', error); }
      }
      if (liveStatus) {
        const generatedAt = liveSnapshot && liveSnapshot.generated_at ? new Date(liveSnapshot.generated_at) : null;
        const staleAfter = Number(liveSnapshot && liveSnapshot.freshness && liveSnapshot.freshness.stale_after_seconds || 900);
        const ageMs = generatedAt && Number.isFinite(generatedAt.getTime()) ? Date.now() - generatedAt.getTime() : Infinity;
        const fresh = ageMs >= 0 && ageMs <= staleAfter * 1000;
        liveStatus.classList.toggle('stale', Boolean(liveSnapshot) && !fresh);
        liveStatus.classList.toggle('unavailable', !liveSnapshot);
        liveStatus.textContent = liveSnapshot
          ? `Live overlay: ${fresh ? 'fresh' : 'stale'} · ${liveSnapshot.market && liveSnapshot.market.asset_count || 0} market observations · updated ${liveSnapshot.generated_at || 'unknown'} · historical yield source unchanged`
          : 'Live overlay: unavailable · historical yield source unchanged';
      }
      const focusAssets = FOCUS_SYMBOLS.map(symbol => assets.find(asset => asset.symbol === symbol)).filter(Boolean);
      if (!assets.length || focusAssets.length !== FOCUS_SYMBOLS.length) throw new Error('CSV is missing one or more focus assets');
      buildMatrix(focusAssets);
      buildLegend(focusAssets);
      buildTimeline(assets, focusAssets);
      buildExplorer(assets, catalog, liveSnapshot);
      document.body.classList.add('matrix-ready');
      console.info(`Loaded ${assets.length} assets into the yield matrix`);
    } catch (error) {
      console.error('Error loading yield matrix:', error);
      if (grid) grid.innerHTML = '<div class="matrix-error">Unable to load yield_data.csv. Serve this folder over a local web server and try again.</div>';
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
