function displayComments(comments) {
  var container = document.getElementById('comments');
  if (!container) return;
  container.innerHTML = '';
  for (var i = 0; i < comments.length; i++) {
    var p = document.createElement('p');
    p.textContent = comments[i];
    container.appendChild(p);
  }
}

displayComments(['First comment', 'Second comment', 'Third comment']);
</script>
</body>
</html>