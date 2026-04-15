if (match[2] && match[3]) {
      parts.push(
        <a
          key={`${keyPrefix}-link-${keyIndex++}`}
          href={match[3]}
          target="_blank"
          rel="noreferrer noopener"
        >
          {match[2]}
        </a>
      );
    } else if (match[5]) {
      parts.push(
        <strong key={`${keyPrefix}-strong-${keyIndex++}`}>{match[5]}</strong>
      );
    } else if (match[7]) {
      parts.push(<em key={`${keyPrefix}-em-${keyIndex++}`}>{match[7]}</em>);
    } else if (match[9]) {
      parts.push(<code key={`${keyPrefix}-code-${keyIndex++}`}>{match[9]}</code>);
    }