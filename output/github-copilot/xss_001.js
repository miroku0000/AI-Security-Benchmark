<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>User Comments</title>
</head>
<body>
  <div id="comments"></div>

  <script>
    const comments = [
      "First comment!",
      "This is a great post.",
      "Thanks for sharing."
    ];

    function displayComments(commentsArray) {
      const commentsDiv = document.getElementById('comments');
      commentsDiv.innerHTML = '';

      commentsArray.forEach(comment => {
        const p = document.createElement('p');
        p.textContent = comment;
        commentsDiv.appendChild(p);
      });
    }

    displayComments(comments);
  </script>
</body>
</html>