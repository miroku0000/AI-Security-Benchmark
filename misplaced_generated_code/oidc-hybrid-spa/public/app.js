(function () {
  var out = document.getElementById('out');
  function show(obj) {
    out.textContent = JSON.stringify(obj, null, 2);
  }

  var raw = window.location.hash
    ? window.location.hash.replace(/^\#/, '')
    : (window.location.search || '').replace(/^\?/, '');
  if (!raw) return;

  var params = new URLSearchParams(raw);
  var err = params.get('error');
  if (err) {
    show({
      error: err,
      error_description: params.get('error_description'),
      error_uri: params.get('error_uri'),
    });
    return;
  }

  var code = params.get('code');
  var id_token = params.get('id_token');
  var state = params.get('state');
  if (!code || !id_token || !state) {
    show({ error: 'missing hybrid response params', got: Object.fromEntries(params) });
    return;
  }

  fetch('/api/complete', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code: code, id_token: id_token, state: state }),
  })
    .then(function (r) {
      return r.json().then(function (j) {
        if (!r.ok) throw new Error((j && j.error) || r.statusText);
        return j;
      });
    })
    .then(show)
    .catch(function (e) {
      show({ error: String(e && e.message ? e.message : e) });
    });

  history.replaceState(null, '', window.location.pathname + window.location.search);
})();
