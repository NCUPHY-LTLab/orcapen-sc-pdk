local function scalar(value)
  if value == nil then return nil end
  if type(value) == 'string' or type(value) == 'number' or type(value) == 'boolean' then
    return tostring(value)
  end
  local kind = pandoc.utils.type(value)
  if kind == 'Inlines' or kind == 'MetaInlines' then
    value = value:walk({RawInline=function(raw) return pandoc.Str(raw.text) end})
    return pandoc.utils.stringify(value)
  end
  if kind == 'MetaString' or kind == 'MetaBool' or kind == 'MetaNumber' then
    return pandoc.utils.stringify(value)
  end
  return nil
end

local function escape(value)
  return value:gsub('&', '&amp;')
    :gsub('<', '&lt;')
    :gsub('>', '&gt;')
    :gsub('"', '&quot;')
    :gsub("'", '&#39;')
end

local function fail(message)
  assert(false, message)
end

local function valid_href(href)
  if href == '' or href:find('%s') or href:find('%c') or href:find('\\', 1, true) then
    return false
  end
  return href:match('^https://[^/?#]+') ~= nil or
    (href:sub(1, 1) == '/' and href:sub(2, 2) ~= '/')
end

function Pandoc(doc)
  if not quarto.doc.is_format('html:js') then return doc end
  local askr = doc.meta.askr
  local languages = askr and askr.languages
  if languages == nil then return doc end

  if type(languages) ~= 'table' or languages.t ~= nil then
    fail('askr.languages: use a mapping with current and items.')
  end
  local current = scalar(languages.current)
  if not current or current == '' then
    fail('askr.languages.current: expected a nonempty scalar language code.')
  end
  if pandoc.utils.type(languages.items) ~= 'List' then
    fail('askr.languages.items: expected a list of {code, label, href} mappings.')
  end
  if #languages.items < 2 then
    fail('askr.languages.items: provide at least two language entries.')
  end

  local entries, codes, current_label = {}, {}, nil
  for _, item in ipairs(languages.items) do
    if type(item) ~= 'table' or item.t ~= nil then
      fail('askr.languages.items: each entry must be a mapping.')
    end
    local code, label, href = scalar(item.code), scalar(item.label), scalar(item.href)
    if not code or code == '' then
      fail('askr.languages.items: each code must be a nonempty scalar.')
    end
    if codes[code] then
      fail('askr.languages.items: language codes must be unique.')
    end
    codes[code] = true
    if not label or label == '' then
      fail('askr.languages.items: each label must be a nonempty scalar.')
    end
    if not href or not valid_href(href) then
      fail('askr.languages.items: each href must be an HTTPS URL or a domain-root /path, not //host.')
    end
    entries[#entries + 1] = {code=code, label=label, href=href}
    if code == current then current_label = label end
  end
  if not current_label then
    fail('askr.languages.current: must match one configured language code.')
  end

  local links = {}
  for _, entry in ipairs(entries) do
    local is_current = entry.code == current
    local current_attrs = is_current and ' class="dropdown-item active" aria-current="true"' or ' class="dropdown-item"'
    local marker = is_current and
      '<span class="askr-language-check" aria-hidden="true">✓</span><span class="visually-hidden">Current</span>' or ''
    links[#links + 1] = '<li><a' .. current_attrs ..
      ' href="' .. escape(entry.href) .. '" lang="' .. escape(entry.code) ..
      '" hreflang="' .. escape(entry.code) .. '">' ..
      '<span class="askr-language-label">' .. escape(entry.label) .. '</span>' ..
      '<span class="askr-language-marker">' .. marker .. '</span></a></li>'
  end

  local accessible_name = 'Language: ' .. current_label
  local html = '<template id="askr-language-config"><div class="askr-language-selector dropdown">' ..
    '<button class="askr-language-toggle dropdown-toggle" type="button" id="askr-language-toggle" ' ..
    'data-bs-toggle="dropdown" aria-expanded="false" aria-label="' .. escape(accessible_name) ..
    '" title="' .. escape(accessible_name) .. '">' ..
    '<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' ..
    '<circle cx="12" cy="12" r="9"></circle><path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18"></path></svg>' ..
    '</button>' ..
    '<ul class="dropdown-menu dropdown-menu-end askr-language-menu" aria-labelledby="askr-language-toggle" aria-label="Available languages">' ..
    table.concat(links) .. '</ul></div></template>'
  quarto.doc.include_text('after-body', html)
  return doc
end
