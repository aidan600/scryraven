// One copy of the answer stays in the DOM, including citation nodes and IDs.
(() => {
  const mobile = matchMedia('(max-width: 760px)');
  const reader = document.querySelector('.reading-scroll');
  const tables = [];

  function longCell(cell) {
    const text = cell.textContent.trim();
    return text.length >= 120 && text.split(/\s+/).length >= 18;
  }

  function hasProse(rows) {
    return rows.some(row => [...row.cells].slice(1).some(longCell));
  }

  function proseRows(table) {
    const headers = [...(table.tHead?.rows[0]?.cells || [])];
    const rows = [...(table.tBodies[0]?.rows || [])];
    if (table.tHead?.rows.length !== 1 || table.tBodies.length !== 1 || table.tFoot ||
        (table.hasAttribute('role') && table.getAttribute('role') !== 'table') ||
        headers.length < 2 || !rows.length ||
        table.querySelector('table, [colspan], [rowspan]')) return null;
    // Repeated labels may copy only inert header formatting. Interactive or
    // ambiguous headers retain their original grid instead of losing content.
    const labels = headers.map(header => header.textContent.trim());
    if (labels.some(label => !label) || new Set(labels).size !== labels.length ||
        headers.some(header => header.hasAttribute('scope') && header.scope !== 'col') ||
        headers.some(header => [...header.querySelectorAll('*')].some(node =>
          !['STRONG', 'EM', 'CODE'].includes(node.tagName) || node.attributes.length))) return null;
    if (rows.some(row => row.cells.length !== headers.length ||
        !row.cells[0].textContent.trim() || row.cells[0].textContent.trim().length > 120)) return null;
    // Prefer Read for sustained prose, leaving short/numeric comparisons alone.
    return hasProse(rows) ? {headers, rows} : null;
  }

  document.querySelectorAll('.answer table').forEach(table => {
    const prose = proseRows(table);
    table.classList.toggle('table-prose-grid', [...table.tBodies].some(body =>
      [...body.rows].some(row => [...row.cells].some(longCell))));
    const wrapper = document.createElement('div');
    wrapper.className = 'answer-table';
    const tools = document.createElement('div');
    tools.className = 'table-tools';
    const viewport = document.createElement('div');
    viewport.className = 'table-scroll';
    const cue = document.createElement('span');
    cue.className = 'table-scroll-cue';
    cue.setAttribute('aria-hidden', 'true');
    cue.hidden = true;
    table.before(wrapper);
    wrapper.append(tools, viewport);
    viewport.append(table);
    if (!table.hasAttribute('role')) table.setAttribute('role', 'table');
    if (table.tHead?.rows.length === 1) [...table.tHead.rows[0].cells].forEach(header => {
      if (header.tagName === 'TH' && header.colSpan === 1 && header.rowSpan === 1 &&
          !header.hasAttribute('scope')) header.scope = 'col';
    });

    const state = {table, wrapper, tools, viewport, cue, prose, choice: 'read', titles: [], labels: []};
    if (prose) {
      table.classList.add('table-prose');
      table.tHead.setAttribute('role', 'rowgroup');
      table.tBodies[0].setAttribute('role', 'rowgroup');
      [...table.rows].forEach(row => row.setAttribute('role', 'row'));
      prose.headers.forEach(header => header.setAttribute('role', 'columnheader'));
      prose.rows.forEach(row => {
        [...row.cells].forEach((cell, column) => {
          cell.setAttribute('role', column ? 'cell' : 'rowheader');
          if (column) {
            const label = document.createElement('div');
            label.className = 'table-read-label';
            label.setAttribute('aria-hidden', 'true');
            label.hidden = true;
            // Only the checked, noninteractive header label is repeated.
            prose.headers[column].childNodes.forEach(node => label.append(node.cloneNode(true)));
            cell.prepend(label);
            state.labels.push(label);
          } else {
            const title = document.createElement('div');
            title.className = 'table-row-title';
            title.append(...cell.childNodes);
            cell.append(title);
            state.titles.push(title);
          }
        });
      });
      const controls = document.createElement('div');
      controls.className = 'table-controls';
      controls.setAttribute('role', 'group');
      controls.setAttribute('aria-label', 'Table layout');
      state.controls = controls;
      state.buttons = ['Read', 'Table'].map(name => {
        const button = document.createElement('button');
        button.type = 'button';
        button.textContent = name;
        button.addEventListener('click', () => {
          const choice = name.toLowerCase();
          if (state.choice === choice) return;
          const edge = reader.getBoundingClientRect().top + tools.offsetHeight;
          const row = prose.rows.find(item => item.getBoundingClientRect().bottom > edge) || prose.rows[0];
          const before = row.getBoundingClientRect().top;
          state.choice = choice;
          layout(state);
          // Keep the current row in view when a long card becomes a grid row.
          reader.scrollTop += row.getBoundingClientRect().top - Math.max(edge + 8, before);
          document.dispatchEvent(new Event('reading-room-table-layout'));
        });
        controls.append(button);
        return button;
      });
      tools.append(controls);
    }
    tools.append(cue);

    function updateOverflow() {
      const read = table.classList.contains('table-is-read');
      const overflow = !read && viewport.scrollWidth - viewport.clientWidth > 2;
      const left = viewport.scrollLeft > 2;
      const right = viewport.scrollLeft + viewport.clientWidth < viewport.scrollWidth - 2;
      cue.hidden = !overflow;
      cue.textContent = `${left ? '← ' : ''}More columns${right ? ' →' : ''}`;
      tools.hidden = (!state.controls || state.controls.hidden) && cue.hidden;
      if (overflow) {
        viewport.tabIndex = 0;
        viewport.setAttribute('role', 'region');
        viewport.setAttribute('aria-label', 'Answer table, scroll horizontally');
      } else {
        viewport.removeAttribute('tabindex');
        viewport.removeAttribute('role');
        viewport.removeAttribute('aria-label');
      }
    }
    state.updateOverflow = updateOverflow;
    viewport.addEventListener('scroll', () => {
      updateOverflow();
      document.dispatchEvent(new Event('reading-room-table-layout'));
    }, {passive: true});
    if (window.ResizeObserver) new ResizeObserver(updateOverflow).observe(viewport);
    tables.push(state);
    layout(state);
  });

  function layout(state) {
    const read = Boolean(state.prose && mobile.matches && state.choice === 'read');
    state.table.classList.toggle('table-is-read', read);
    state.labels.forEach(label => label.hidden = !read);
    state.titles.forEach(title => {
      if (read) {
        title.setAttribute('role', 'heading');
        title.setAttribute('aria-level', '3');
      } else {
        title.removeAttribute('role');
        title.removeAttribute('aria-level');
      }
    });
    if (state.controls) {
      state.controls.hidden = !mobile.matches;
      state.buttons.forEach(button => button.setAttribute('aria-pressed', String(button.textContent.toLowerCase() === state.choice)));
    }
    state.updateOverflow();
  }
  mobile.addEventListener('change', () => {
    tables.forEach(layout);
    document.dispatchEvent(new Event('reading-room-table-layout'));
  });
  window.addEventListener('resize', () => tables.forEach(state => state.updateOverflow()));
})();
