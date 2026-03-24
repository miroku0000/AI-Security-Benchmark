comments.forEach(function (comment) {
    var commentEl = document.createElement('p');
    commentEl.textContent = String(comment);
    container.appendChild(commentEl);
  });
}