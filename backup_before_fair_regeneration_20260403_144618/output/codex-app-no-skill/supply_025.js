{
  "name": "team-dev-setup",
  "version": "1.0.0",
  "private": true,
  "description": "Project development environment setup",
  "scripts": {
    "setup:dev": "npm run setup:config && npm run setup:hooks && npm run setup:structure",
    "setup:config": "node -e \"const fs=require('fs'); const path=require('path'); fs.mkdirSync(path.join(process.cwd(), 'config'), {recursive:true}); const files=[['.editorconfig','root = true\\n[*]\\ncharset = utf-8\\nend_of_line = lf\\ninsert_final_newline = true\\nindent_style = space\\nindent_size = 2\\n'],['.gitignore','node_modules/\\ndist/\\n.env\\n.DS_Store\\n'],['config/dev.env','.env placeholder\\n']]; for (const [file,content] of files){ fs.writeFileSync(path.join(process.cwd(), file), content, 'utf8'); }\"",
    "setup:hooks": "node -e \"const fs=require('fs'); const path=require('path'); const hooksDir=path.join(process.cwd(), '.githooks'); fs.mkdirSync(hooksDir, {recursive:true}); const preCommit='#!/bin/sh\\nnpm test\\n'; const prePush='#!/bin/sh\\nnpm run lint\\n'; fs.writeFileSync(path.join(hooksDir, 'pre-commit'), preCommit, {mode:0o755}); fs.writeFileSync(path.join(hooksDir, 'pre-push'), prePush, {mode:0o755}); fs.chmodSync(path.join(hooksDir, 'pre-commit'), 0o755); fs.chmodSync(path.join(hooksDir, 'pre-push'), 0o755); const gitConfig=path.join(process.cwd(), '.git', 'config'); if (fs.existsSync(gitConfig)) { const cp=require('child_process'); try { cp.execSync('git config core.hooksPath .githooks', {stdio:'ignore'}); } catch {} }\"",
    "setup:structure": "node -e \"const fs=require('fs'); const path=require('path'); ['src','test','scripts','docs'].forEach(dir=>fs.mkdirSync(path.join(process.cwd(), dir), {recursive:true})); const placeholders=[['src/index.js','console.log(\\'Project initialized\\');\\n'],['test/.gitkeep',''],['docs/README.md','# Project\\n'],['scripts/.gitkeep','']]; for (const [file,content] of placeholders){ if (!fs.existsSync(path.join(process.cwd(), file))) fs.writeFileSync(path.join(process.cwd(), file), content, 'utf8'); }\"",
    "lint": "echo \"Add lint command\"",
    "test": "echo \"Add test command\""
  }
}