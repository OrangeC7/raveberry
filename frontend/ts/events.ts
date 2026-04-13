import ReconnectingWebSocket from 'reconnecting-websocket';
import {updateState, reconnect} from './base.js';

let socketUrl = window.location.host + '/state/';
if (window.location.protocol == 'https:') {
  socketUrl = 'wss://' + socketUrl;
} else {
  socketUrl = 'ws://' + socketUrl;
}

const stateSocket = new ReconnectingWebSocket(socketUrl, [], {});
let shuttingDown = false;
let hideReconnectBannerTimer: number | null = null;

function shutdownStateSocket(reason = 'page shutdown') {
  if (shuttingDown) {
    return;
  }
  shuttingDown = true;

  if (hideReconnectBannerTimer !== null) {
    window.clearTimeout(hideReconnectBannerTimer);
    hideReconnectBannerTimer = null;
  }

  try {
    // reconnecting-websocket supports a third options arg at runtime.
    // keepClosed=true is the important part: do not reconnect while unloading.
    (stateSocket as any).close(1000, reason, {keepClosed: true, fastClose: true});
  } catch (_err) {
    try {
      stateSocket.close(1000, reason);
    } catch (_err2) {
      // ignore
    }
  }
}

stateSocket.addEventListener('message', (e) => {
  if (shuttingDown) {
    return;
  }
  const newState = JSON.parse(e.data);
  updateState(newState);
});

let firstConnect = true;
stateSocket.addEventListener('open', () => {
  if (shuttingDown) {
    shutdownStateSocket('shutdown-after-open');
    return;
  }

  if (!firstConnect) {
    reconnect();
    $('#disconnected-banner').slideUp('fast');
    $('#reconnected-banner').slideDown('fast');

    if (hideReconnectBannerTimer !== null) {
      window.clearTimeout(hideReconnectBannerTimer);
    }
    hideReconnectBannerTimer = window.setTimeout(function() {
      $('#reconnected-banner').slideUp('fast');
    }, 2000);
  }

  firstConnect = false;
});

stateSocket.addEventListener('close', () => {
  if (shuttingDown) {
    return;
  }
  $('#disconnected-banner').slideDown('fast');
});

window.addEventListener('message', (event) => {
  if (event.origin !== window.location.origin) {
    return;
  }
  if (event.data && event.data.type === 'furatic:shutdown-state-socket') {
    shutdownStateSocket('parent-mode-switch');
  }
});

addEventListener('pagehide', () => {
  shutdownStateSocket('pagehide');
}, {capture: true});

addEventListener('beforeunload', () => {
  shutdownStateSocket('beforeunload');
}, {capture: true});
