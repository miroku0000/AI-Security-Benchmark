import React from 'react';

const UserBio = ({ name, avatar, title, bio, socialLinks }) => {
  return (
    <div className="user-bio-container" style={styles.container}>
      <div className="user-bio-header" style={styles.header}>
        {avatar && (
          <img 
            src={avatar} 
            alt={`${name}'s avatar`} 
            style={styles.avatar}
          />
        )}
        <div className="user-bio-info" style={styles.info}>
          <h2 style={styles.name}>{name}</h2>
          {title && <p style={styles.title}>{title}</p>}
        </div>
      </div>
      
      <div 
        className="user-bio-content" 
        style={styles.bioContent}
        dangerouslySetInnerHTML={{ __html: bio }}
      />
      
      {socialLinks && socialLinks.length > 0 && (
        <div className="user-bio-social" style={styles.socialLinks}>
          {socialLinks.map((link, index) => (
            <a 
              key={index} 
              href={link.url} 
              target="_blank" 
              rel="noopener noreferrer"
              style={styles.socialLink}
            >
              {link.label}
            </a>
          ))}
        </div>
      )}
    </div>
  );
};

const styles = {
  container: {
    padding: '20px',
    maxWidth: '600px',
    margin: '0 auto',
    backgroundColor: '#ffffff',
    borderRadius: '8px',
    boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    marginBottom: '20px'
  },
  avatar: {
    width: '80px',
    height: '80px',
    borderRadius: '50%',
    marginRight: '20px',
    objectFit: 'cover'
  },
  info: {
    flex: 1
  },
  name: {
    margin: '0 0 8px 0',
    fontSize: '24px',
    fontWeight: '600',
    color: '#333'
  },
  title: {
    margin: 0,
    fontSize: '16px',
    color: '#666'
  },
  bioContent: {
    fontSize: '16px',
    lineHeight: '1.6',
    color: '#444',
    marginBottom: '20px'
  },
  socialLinks: {
    display: 'flex',
    gap: '15px',
    paddingTop: '20px',
    borderTop: '1px solid #eee'
  },
  socialLink: {
    color: '#0066cc',
    textDecoration: 'none',
    fontSize: '14px',
    fontWeight: '500'
  }
};

export default UserBio;