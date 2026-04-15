comments.forEach(function (comment) {
    const commentElement = document.createElement('p');
    commentElement.textContent = comment;
    commentsDiv.appendChild(commentElement);
  });
}