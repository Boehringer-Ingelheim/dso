-- Add the disclaimer from the `disclaimer` metadata as a quarto callout at the top of the document.
-- Registered by DSO at the `pre-ast` entry point so that quarto renders the callout in all output formats.
function Pandoc(doc)
  local disclaimer = doc.meta.disclaimer
  if disclaimer == nil or disclaimer.title == nil or disclaimer.text == nil then
    return doc
  end
  local body = disclaimer.text
  if pandoc.utils.type(body) ~= "Blocks" then
    body = { pandoc.Para(body) }
  end
  local callout = pandoc.Div(body, pandoc.Attr("", { "callout-important" }, { title = pandoc.utils.stringify(disclaimer.title) }))
  doc.blocks:insert(1, callout)
  return doc
end
