-- Trusted local HTML charts keep their own interaction engine and resources.
local serial = 0
local function value(v) return v and pandoc.utils.stringify(v) or nil end
local function fail(message) assert(false, 'askr-chart-view: ' .. message) end
local function escape(s)
  return s:gsub('&', '&amp;'):gsub('<', '&lt;'):gsub('>', '&gt;'):gsub('"', '&quot;'):gsub("'", '&#39;')
end

return {
  ['askr-chart-view'] = function(args, kwargs, meta, raw_args, context)
    for key, _ in pairs(kwargs) do
      if key ~= 'src' and key ~= 'mode' and key ~= 'label' then fail('unknown argument ' .. key .. '.') end
    end
    local src = value(rawget(kwargs, 'src'))
    local mode = value(rawget(kwargs, 'mode')) or 'inline'
    local label = value(rawget(kwargs, 'label')) or 'View chart'
    if #args > 0 or not src or src == '' then fail('provide a local HTML file using src="plots/chart.html".') end
    if mode ~= 'inline' and mode ~= 'button' then fail('mode must be inline or button.') end
    if label == '' then fail('label must not be empty.') end
    if src:match('^[%a][%w+.-]*:') or src:sub(1, 2) == '//' or src:find('\\', 1, true) or src:find('[?#%c]') then
      fail('src must be a same-site local HTML file; external URLs, queries and fragments are unsupported.')
    end
    if not src:lower():match('%.html$') then fail('src must name a local .html export.') end
    local absolute
    if src:sub(1, 1) == '/' then
      if not quarto.project.directory then fail('project-root src paths require a Quarto project.') end
      absolute = pandoc.path.join({quarto.project.directory, src:sub(2)})
    else
      absolute = quarto.utils.resolve_path_relative_to_document(src)
    end
    absolute = pandoc.path.normalize(absolute)
    local file = io.open(absolute, 'rb')
    if not file then fail('local HTML export not found: ' .. src) end
    file:close()
    local relative = pandoc.path.make_relative(absolute, pandoc.path.directory(quarto.doc.input_file), true)
    if not quarto.doc.is_format('html:js') then return pandoc.Link({pandoc.Str(label)}, relative) end
    if mode == 'inline' and context == 'inline' then fail('inline mode requires a standalone shortcode block.') end
    quarto.doc.add_resource(absolute)
    quarto.doc.add_html_dependency({name='askr-chart-viewer', version='1', scripts={'chart-viewer.js'}, stylesheets={'chart-viewer.css'}})
    serial = serial + 1
    local lang = pandoc.utils.stringify(meta.lang or '')
    local chinese = lang:match('^zh') ~= nil
    local source_label = chinese and '開啟原始圖表' or 'Open source chart'
    local title = escape(label)
    local url = escape(relative)
    local attr = ' class="askr-chart-view" data-askr-chart-mode="' .. mode .. '" data-askr-chart-title="' .. title .. '"'
    local link = '<a class="askr-chart-open" href="' .. url .. '">' .. title .. '</a>'
    if mode == 'button' then
      local html = '<span' .. attr .. '>' .. link .. '</span>'
      return context == 'inline' and pandoc.RawInline('html', html) or pandoc.RawBlock('html', html)
    end
    return pandoc.RawBlock('html', '<div' .. attr .. '><div class="askr-chart-toolbar">' .. link ..
      '<a class="askr-chart-source" href="' .. url .. '">' .. source_label .. '</a></div>' ..
      '<div class="askr-chart-frame-wrap"><iframe class="askr-chart-frame" src="' .. url .. '" title="' .. title ..
      '" loading="lazy"></iframe></div></div>')
  end
}
