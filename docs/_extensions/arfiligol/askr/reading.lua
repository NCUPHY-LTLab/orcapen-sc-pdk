local function text(value)
  if type(value) == 'boolean' or type(value) == 'number' then return tostring(value) end
  if pandoc.utils.type(value) == 'Inlines' then
    value = value:walk({RawInline=function(raw) return pandoc.Str(raw.text) end})
  end
  return pandoc.utils.stringify(value)
end
local function escape(value)
  return value:gsub('&', '&amp;'):gsub('<', '&lt;'):gsub('>', '&gt;'):gsub('"', '&quot;')
end

function Pandoc(doc)
  if not quarto.doc.is_format('html:js') then return doc end
  quarto.doc.add_html_dependency({name='askr-reading', version='0.9.0', scripts={'reading.js'}})
  local askr = doc.meta.askr or {}
  local width = askr['reading-width'] and text(askr['reading-width']) or 'normal'
  assert(width == 'normal' or width == 'wide', 'askr.reading-width: expected normal or wide.')
  if width == 'wide' then
    quarto.doc.include_text('in-header', '<script>document.documentElement.classList.add("askr-reading-wide");</script>')
  end
  local facts = askr['page-facts']
  if facts == nil then return doc end
  assert(pandoc.utils.type(facts) == 'List', 'askr.page-facts: expected a list of {key, label} mappings.')
  local rows = {}
  for _, fact in ipairs(facts) do
    assert(fact.key and fact.label, 'askr.page-facts: each entry requires key and label.')
    local key, label = text(fact.key), text(fact.label)
    local value = doc.meta[key]
    if value ~= nil then
      local kind = pandoc.utils.type(value)
      assert(kind ~= 'List' and kind ~= 'table' and kind ~= 'Blocks', 'askr page fact ' .. key .. ': expected a flat scalar.')
      local rendered = text(value)
      if rendered ~= '' then
        rows[#rows+1] = '<div class="askr-page-fact"><dt>' .. escape(label) .. '</dt><dd>' .. escape(rendered) .. '</dd></div>'
      end
    end
  end
  if #rows > 0 then
    quarto.doc.include_text('after-body', '<template id="askr-page-facts"><dl class="askr-page-facts">' .. table.concat(rows) .. '</dl></template>')
  end
  return doc
end
