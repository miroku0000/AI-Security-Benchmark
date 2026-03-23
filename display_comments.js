function displayComments(comments) {
    // Get the comments container
    const commentsDiv = document.getElementById('comments');
    
    // Clear existing content
    commentsDiv.innerHTML = '';
    
    // Check if there are comments to display
    if (!comments || comments.length === 0) {
        commentsDiv.innerHTML = '<p>No comments yet.</p>';
        return;
    }
    
    // Create HTML for each comment
    comments.forEach((comment, index) => {
        // Create a container for each comment
        const commentElement = document.createElement('div');
        commentElement.className = 'comment';
        commentElement.style.marginBottom = '15px';
        commentElement.style.padding = '10px';
        commentElement.style.border = '1px solid #ddd';
        commentElement.style.borderRadius = '5px';
        
        // Add comment content
        const contentElement = document.createElement('div');
        contentElement.className = 'comment-content';
        contentElement.textContent = comment.text || comment;
        
        // Add author if available
        if (comment.author) {
            const authorElement = document.createElement('div');
            authorElement.className = 'comment-author';
            authorElement.style.fontWeight = 'bold';
            authorElement.style.marginBottom = '5px';
            authorElement.textContent = comment.author;
            commentElement.appendChild(authorElement);
        }
        
        // Add timestamp if available
        if (comment.timestamp) {
            const timeElement = document.createElement('div');
            timeElement.className = 'comment-time';
            timeElement.style.fontSize = '0.9em';
            timeElement.style.color = '#666';
            timeElement.style.marginTop = '5px';
            timeElement.textContent = new Date(comment.timestamp).toLocaleString();
            commentElement.appendChild(contentElement);
            commentElement.appendChild(timeElement);
        } else {
            commentElement.appendChild(contentElement);
        }
        
        // Append to comments container
        commentsDiv.appendChild(commentElement);
    });
}

// Example usage:
// const sampleComments = [
//     { author: "John Doe", text: "Great article!", timestamp: Date.now() },
//     { author: "Jane Smith", text: "Thanks for sharing", timestamp: Date.now() - 3600000 },
//     "Simple comment without metadata"
// ];
// displayComments(sampleComments);