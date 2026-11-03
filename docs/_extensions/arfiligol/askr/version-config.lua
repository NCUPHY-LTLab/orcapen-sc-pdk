-- Embed the project-local version manifest so the selector can be ready at
-- first paint. The browser still fetches the deployed manifest as authority.
local function project_manifest()
  local project_dir = quarto.project and quarto.project.directory
  if not project_dir then return nil end
  local path = pandoc.path.join({project_dir, 'askr-versions.json'})
  local file = io.open(path, 'rb')
  if not file then return nil end
  local contents = file:read('*a')
  file:close()
  if not contents or contents == '' then return nil end
  local ok = pcall(quarto.json.decode, contents)
  if not ok then return nil end
  return contents:gsub('<', '\\u003c')
end

function Pandoc(doc)
  if not quarto.doc.is_format('html:js') then return doc end
  local contents = project_manifest()
  if contents then
    quarto.doc.include_text('after-body', '<script type="application/json" id="askr-versions-local">' ..
      contents .. '</script>')
  end
  return doc
end
