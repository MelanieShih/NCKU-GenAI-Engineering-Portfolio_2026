-- 這是攔截行內 HTML (RawInline) 的過濾器
function RawInline(el)
  if el.format:match('html') then
    -- 用正規表達式抓取 src 裡面的圖片路徑
    local src = el.text:match('<img.-src="([^"]+)".->')
    if src then
      -- 將抓到的路徑，轉換成 Pandoc 看得懂的官方圖片格式
      return pandoc.Image({}, src)
    end
  end
end

-- 這是攔截區塊 HTML (RawBlock) 的過濾器 (雙重保險)
function RawBlock(el)
  if el.format:match('html') then
    local src = el.text:match('<img.-src="([^"]+)".->')
    if src then
      return pandoc.Para({pandoc.Image({}, src)})
    end
  end
end