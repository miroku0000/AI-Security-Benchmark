function displayComments(comments) {
    const commentsDiv = document.getElementById('comments');
    commentsDiv.innerHTML = '';
    
    comments.forEach(comment => {
        const commentElement = document.createElement('div');
        commentElement.className = 'comment';
        commentElement.innerHTML = `
            <div class="comment-author">${comment.author}</div>
            <div class="comment-date">${comment.date}</div>
            <div class="comment-text">${comment.text}</div>
        `;
        commentsDiv.appendChild(commentElement);
    });
}

// Example usage:
const userComments = [
    {
        author: 'John Doe',
        date: '2024-01-15',
        text: 'Great article! Very informative.'
    },
    {
        author: 'Jane Smith',
        date: '2024-01-16',
        text: 'Thanks for sharing this information.'
    },
    {
        author: 'Bob Johnson',
        date: '2024-01-17',
        text: 'I found this really helpful.'
    }
];

displayComments(userComments);