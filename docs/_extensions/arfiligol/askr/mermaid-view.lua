local function has_class(div, name)
  return div.classes and div.classes:includes(name)
end

local function fail(message)
  assert(false, message)
end

local function native_mermaid_count(div)
  local count = 0
  div:walk({RawBlock=function(block)
    if block.format == 'html' then
      for _ in block.text:gmatch('<pre%s+class="[^"]*mermaid%-js[^"]*"') do
        count = count + 1
      end
    end
    return nil
  end})
  return count
end

function Pandoc(doc)
  if not quarto.doc.is_format('html:js') then return doc end

  local lightbox_disabled = doc.meta.lightbox == false or doc.meta['askr-viewer-disabled'] == true
  return doc:walk({Div=function(div)
    if not has_class(div, 'askr-mermaid-view') then return nil end
    if lightbox_disabled then
      fail('askr-mermaid-view: lightbox: false conflicts with a Mermaid viewer wrapper.')
    end
    if #div.content ~= 1 or div.content[1].t ~= 'Div' or
       not div.content[1].classes:includes('cell') then
      fail('askr-mermaid-view: wrap exactly one native Mermaid code cell.')
    end
    if native_mermaid_count(div) ~= 1 then
      fail('askr-mermaid-view could not find exactly one Quarto browser-rendered Mermaid source block; image-rendered Mermaid output is incompatible.')
    end

    local label = div.attributes['view-label']
    if label ~= nil and label:match('^%s*$') then
      fail('askr-mermaid-view.view-label: expected a nonempty label.')
    end
    div.attributes['data-askr-mermaid-view'] = 'true'
    if label then div.attributes['data-askr-mermaid-label'] = label end
    return div
  end})
end
