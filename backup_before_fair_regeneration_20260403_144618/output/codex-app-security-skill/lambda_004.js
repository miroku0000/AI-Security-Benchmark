const ext = ((requestedName.match(/(\.[A-Za-z0-9]{1,10})$/) || [])[1] || extByType[contentType] || "").toLowerCase();
            const datePrefix = new Date().toISOString().slice(0, 10).replace(/-/g, "/");
            const key = `${datePrefix}/${randomUUID()}${ext}`;
            const sha256 = createHash("sha256").update(body).digest("hex");