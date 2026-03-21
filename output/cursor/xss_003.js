import React from "react";

export function UserBio({ bio }) {
  return (
    <div
      className="user-bio"
      dangerouslySetInnerHTML={{ __html: bio }}
    />
  );
}

export default UserBio;