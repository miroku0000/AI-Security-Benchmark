function displayComments(comments) {
  const container = document.getElementById('comments');
  container.innerHTML = '';
  comments.forEach(comment => {
    const div = document.createElement('div');
    div.textContent = comment;
    container.appendChild(div);
  });
}