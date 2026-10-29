/* HNLS responsive navigation; no lighting or playback calls. */
(() => {
  'use strict';
  const button = document.getElementById('hnls-menu-toggle');
  const navigation = document.getElementById('hnls-navigation');
  if (!button || !navigation) return;
  const toolsButton = document.getElementById('hnls-tools-window');
  const status = document.getElementById('hnls-window-status');
  const inTools = new URLSearchParams(window.location.search).get('hnls_tools') === '1';
  if (inTools) {
    document.body.classList.add('hnls-tools-window');
    document.title = 'HNLS tools · ' + document.title;
    toolsButton.textContent = 'Close tools window';
    toolsButton.addEventListener('click', () => window.close());
    // The separate tools script provides a fixed toolbar; it never navigates itself.
  } else if (toolsButton) {
    let toolsWindow = null;
    toolsButton.addEventListener('click', () => {
      if (toolsWindow && !toolsWindow.closed) { toolsWindow.focus(); return; }
      const url = new URL('/song-designer', window.location.origin);
      url.searchParams.set('hnls_tools', '1');
      toolsWindow = window.open(url.href, 'hnls-tools', 'popup=yes,width=620,height=820,resizable=yes,scrollbars=yes');
      status.hidden = false;
      if (toolsWindow) {
        toolsWindow.focus();
        status.textContent = 'Tools opened in a separate window. Drag it to your other monitor. Changes apply when you save.';
      } else {
        status.textContent = 'The browser blocked the tools window. Allow pop-ups for this HNLS address, then try again.';
      }
    });
  }
  const setOpen = (open, focusButton = false) => {
    navigation.dataset.open = String(open);
    button.setAttribute('aria-expanded', String(open));
    button.querySelector('span').textContent = open ? 'Close' : 'Menu';
    if (focusButton) button.focus();
  };
  button.addEventListener('click', () => setOpen(button.getAttribute('aria-expanded') !== 'true'));
  navigation.addEventListener('click', event => {
    if (event.target.closest('a') && window.matchMedia('(max-width: 800px)').matches) setOpen(false);
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && button.getAttribute('aria-expanded') === 'true') setOpen(false, true);
  });
})();
