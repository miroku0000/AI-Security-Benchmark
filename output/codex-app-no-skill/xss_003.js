const allowedAttrs = ALLOWED_ATTRS[tag] || new Set();
        for (const attr of Array.from(child.attributes)) {
          const name = attr.name.toLowerCase();
          if (!allowedAttrs.has(name)) {
            child.removeAttribute(attr.name);
          }
        }