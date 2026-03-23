import React from "react";

export default function UserBio({ bio }) {
  if (bio == null || bio === "") {
    return null;
  }

  return (
    <div
      className="user-bio"
      dangerouslySetInnerHTML={{ __html: String(bio) }}
    />
  );
}