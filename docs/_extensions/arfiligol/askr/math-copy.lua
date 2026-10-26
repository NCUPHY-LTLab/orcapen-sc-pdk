-- Keep native Math nodes intact for Quarto's numbering and cross references.
-- Attributes hold copy source outside the search index's text content.
function Pandoc(doc)
  if not quarto.doc.is_format('html:js') then return doc end
  local enabled = not (doc.meta.askr and doc.meta.askr['math-copy'] == false)
  if doc.meta['askr-math-copy'] ~= nil then enabled = doc.meta['askr-math-copy'] ~= false end
  if not enabled then return doc end
  local function capture(block)
    local source, count = nil, 0
    for _, inline in ipairs(block.content) do
      -- Quarto reads equation attributes from trailing text after user filters.
      if inline.t == 'Str' and inline.text:gsub('[{}]', '') == '.no-math-copy' then return nil end
      if inline.t == 'Math' and inline.mathtype == 'DisplayMath' then
        source, count = inline.text, count + 1
      end
    end
    if count ~= 1 then return nil end
    return pandoc.Div({block}, pandoc.Attr('', {'askr-copyable-math'}, {['data-askr-tex']=source})), false
  end
  return doc:walk({traverse='topdown',
    Div=function(div)
      if div.classes:includes('no-math-copy') then return div, false end
    end,
    Span=function(span)
      if span.classes:includes('no-math-copy') then return span, false end
    end,
    Para=capture,
    Plain=capture
  })
end
