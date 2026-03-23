function displayComments(commentList) {
        var container = document.getElementById("comments");
        if (!(container instanceof HTMLDivElement)) {
          return;
        }