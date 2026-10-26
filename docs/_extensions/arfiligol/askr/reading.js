(() => {
  function region(element, label) {
    element.setAttribute('role', 'region');
    element.setAttribute('tabindex', '0');
    if (!element.hasAttribute('aria-label') && !element.hasAttribute('aria-labelledby')) {
      element.setAttribute('aria-label', label);
    }
  }
  function initialize() {
    const main = document.querySelector('main.content');
    if (!main) return;
    main.querySelectorAll('table').forEach(table => {
      let wrapper = table.closest('.askr-table-scroll, .table-responsive');
      if (!wrapper || !main.contains(wrapper)) {
        wrapper = document.createElement('div');
        table.before(wrapper);
        wrapper.append(table);
      }
      wrapper.classList.add('askr-table-scroll');
      region(wrapper, table.caption?.textContent.trim() || 'Scrollable table');
    });
    main.querySelectorAll('.askr-wide-figure').forEach(figure => {
      region(figure, figure.querySelector('figcaption')?.textContent.trim() || 'Scrollable figure');
      const sizeDrawings = () => figure.querySelectorAll('svg').forEach(svg => {
          // Mermaid's viewBox records its natural drawing extent.
          const width = svg.viewBox?.baseVal.width;
          if (width > 0) {
            svg.style.width = `${width}px`;
            svg.style.maxWidth = 'none';
          }
        });
      sizeDrawings();
      // Mermaid renders asynchronously and can replace SVGs on theme changes.
      new MutationObserver(sizeDrawings).observe(figure, {childList: true, subtree: true});
    });
    const template = document.getElementById('askr-page-facts');
    const title = document.getElementById('title-block-header');
    if (template && title) {
      const facts = template.content.cloneNode(true);
      const description = title.querySelector('.description');
      if (description) description.after(facts);
      else (title.querySelector('.quarto-title') || title).append(facts);
      template.remove();
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize);
  else initialize();
})();
