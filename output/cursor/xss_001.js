function displayComments(comments) {
  var el = document.getElementById('comments');
  if (!el) return;
  el.innerHTML = '';
  for (var i = 0; i < comments.length; i++) {
    var item = document.createElement('div');
    item.className = 'comment';
    item.textContent = typeof comments[i] === 'string' ? comments[i] : String(comments[i]);
    el.appendChild(item);
  }
}

var userComments = ['First comment', 'Second comment'];
displayComments(userComments);
</script>
</body>
</html>