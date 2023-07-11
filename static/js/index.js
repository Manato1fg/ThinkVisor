let sentComments = [] // 自分が送信したコメント
let sentCommentsEmbedded = [] // 自分が送信したコメントの埋め込みベクトル
let labels = []
for (let i = 0; i < sentences.length; i++) {
  labels.push(sentences[i]) // ラベル用に
}

let preferences = [] // 自分の好み

function color(i, max) {
  let res = []
  for (let j = 0; j < max; j++) {
    if (j === i) {
      res.push("#24c938")
    } else {
      res.push("#aaaaaa")
    }
  }
  return res
}

// HSV色空間の生成
function HSVtoRGB(h, s, v) {
  let r, g, b
  let i = Math.floor(h * 6)
  let f = h * 6 - i
  let p = v * (1 - s)
  let q = v * (1 - f * s)
  let t = v * (1 - (1 - f) * s)
  switch (i % 6) {
    case 0:
      ;(r = v), (g = t), (b = p)
      break
    case 1:
      ;(r = q), (g = v), (b = p)
      break
    case 2:
      ;(r = p), (g = v), (b = t)
      break
    case 3:
      ;(r = p), (g = q), (b = v)
      break
    case 4:
      ;(r = t), (g = p), (b = v)
      break
    case 5:
      ;(r = v), (g = p), (b = q)
      break
  }
  return [r * 255, g * 255, b * 255]
}

function rgbToString(rgb) {
  return "rgb(" + rgb[0] + "," + rgb[1] + "," + rgb[2] + ")"
}

function rgbToHex(rgb, a) {
  return "rgb(" + rgb[0] + "," + rgb[1] + "," + rgb[2] + "," + a + ")"
}

function _createColorArray(n) {
  let res = []
  for (let i = 0; i < n; i++) {
    res.push(HSVtoRGB(i / n, 1, 1))
  }
  return res
}

function createColorArray(colors) {
  let res = []
  for (let i = 0; i < colors.length; i++) {
    res.push(rgbToString(colors[i]))
  }
  return res
}

function createColorArrayWithAlpha(colors, alpha = 0.2) {
  let res = []
  for (let i = 0; i < colors.length; i++) {
    res.push(rgbToHex(colors[i], alpha))
  }
  return res
}

let topicGraphData = {
  labels: mostLikelyTopics,
  datasets: [
    {
      label: "ユーザーの意見",
      data: graphData,
      borderColor: "#00000000",
      backgroundColor: color(topicIndex, mostLikelyTopics.length),
      pointStyle: "circle",
      pointRadius: sizeData, // 60 +- 20
      pointHoverRadius: hoverData,
    },
  ],
}

let topicGraphConfig = {
  type: "scatter",
  data: topicGraphData,
  options: {
    responsive: true,
    maintainAspectRatio: false,
    onClick: async (e) => {
      if (e.chart.tooltip.opacity === 0) {
        return
      }
    },
    interaction: {
      mode: "index",
    },
    scales: {
      x: {
        display: false,
        grid: {
          display: false,
        },
      },
      y: {
        display: false,
        grid: {
          display: false,
        },
      },
    },
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        callbacks: {
          label: function (context) {
            idx = context.dataIndex
            selectedComment =
              sentences[idx] ?? sentComments[idx - sentences.length]
            return ""
          },
          footer: function (context) {
            return "クリックして観点別コメントを見る"
          },
        },
      },
      zoom: {
        pan: {
          enabled: false,
          mode: "xy",
        },
        zoom: {
          wheel: {
            enabled: false,
          },
          pinch: {
            enabled: false,
          },
          mode: "xy",
          onZoomComplete({ chart }) {
            const zoomLevel = chart.getZoomLevel()
            // console.log(zoomLevel)
          },
        },
      },
    },
  },
}

let _colors = _createColorArray(topics[topicIndex].length)
let analysisData = {
  // よく出てくる単語
  labels: topics[topicIndex],
  datasets: [
    {
      axis: "y",
      label: "相対的な頻度",
      data: probs[topicIndex],
      fill: false,
      backgroundColor: createColorArrayWithAlpha(_colors),
      borderColor: createColorArray(_colors),
      borderWidth: 1,
    },
  ],
}
let analysisConfig = {
  type: "bar",
  data: analysisData,
  options: {
    indexAxis: "y",
    animation: false,
  },
}

const MIN_LIKE_COUNT = 5

function changePage(page) {
  // ページの移動
  window.location.href = "/?data_index=" + page
}

function draw(animation = true) {
  if (window.topicChart.destroy) {
    window.topicChart.destroy()
    window.topicChart = null
  }

  if (window.analysisChart.destroy) {
    window.analysisChart.destroy()
    window.analysisChart = null
  }
  const ctx = document.getElementById("topicChart")
  topicGraphConfig.options.animation = animation
  window.topicChart = new Chart(ctx, topicGraphConfig) // 描画更新

  const ctx2 = document.getElementById("analysisChart")
  window.analysisChart = new Chart(ctx2, analysisConfig) // 描画更新
}

let selectedComment = "まだコメントを選択していません"
let idx = -1

document.addEventListener("DOMContentLoaded", () => {
  draw()
  let commentIndex = 0
  const maxCommentIndex = randomIndices.length - 1
  const updateComment = () => {
    fetch(
      "/randomComment?data_index=" +
        dataIndex +
        "&index=" +
        randomIndices[commentIndex]
    ).then((response) => {
      if (response.ok) {
        response.json().then((d) => {
          document.getElementById("represent-comment").textContent =
            d["comment"]
          //一番上にスクロール
          document.getElementById("represent-comment").scrollTop = 0
          document.getElementById("prev-button").disabled = false

          if (topicIndex !== d["topic_index"]) {
            // 色変更
            topicGraphData.datasets[0].backgroundColor = color(
              topicIndex,
              mostLikelyTopics.length
            )

            analysisData.labels = topics[topicIndex]
            analysisData.datasets[0].data = probs[topicIndex]
            _colors = _createColorArray(topics[topicIndex].length)
            analysisData.datasets[0].backgroundColor =
              createColorArrayWithAlpha(_colors)
            analysisData.datasets[0].borderColor = createColorArray(_colors)
            // 再描画
          }
          topicIndex = d["topic_index"]
          draw((animation = true))

          const index = randomIndices[commentIndex]
          for (let i = 0; i < preferences.length; i++) {
            if (preferences[i].id === index) {
              if (preferences[i].reaction === 1) {
                likeButton.classList.add("selected")
                dislikeButton.classList.remove("selected")
              } else if (preferences[i].reaction === -1) {
                dislikeButton.classList.add("selected")
                likeButton.classList.remove("selected")
              }
              return
            }
          }
          likeButton.classList.remove("selected")
          dislikeButton.classList.remove("selected")
        })
      } else {
        console.log("Network response was not ok.")
      }
    })
  }

  const ai_analysis = document.getElementById("ai-analysis-button")
  function updateAnalysisButton() {
    const innerHTML = `<span class="material-symbols-outlined">neurology</span><span>あなたの意見をAIが分析&nbsp;{{count}}</span>`
    const count = preferences.filter((p) => p.reaction !== 0).length
    ai_analysis.innerHTML = innerHTML.replace(
      "{{count}}",
      `${count} / ${MIN_LIKE_COUNT}`
    )
    if (count >= MIN_LIKE_COUNT) {
      ai_analysis.classList.remove("disabled")
    } else {
      ai_analysis.classList.add("disabled")
    }
  }

  ai_analysis.addEventListener("click", async () => {
    if (ai_analysis.classList.contains("disabled")) {
      return
    }

    document.getElementById("analysis-wrapper").style.display = "block"

    formData = new FormData()
    formData.append("preferences", JSON.stringify(preferences))
    formData.append("data_index", dataIndex)

    let commentPhase = true
    let commentMD = ""
    const decoder = new TextDecoder()
    fetch("/analysis", {
      method: "POST",
      body: formData,
    })
      .then((response) => {
        if (response.ok) {
          return response.body.getReader()
        }
      })
      .then((reader) => {
        function readChunk({ done, value }) {
          if (done === true) {
            return
          }
          if (decoder.decode(value) === "END_ANALYSIS") {
            commentPhase = false
            document.getElementById("analysis-comment").innerHTML =
              md2html(commentMD)
            reader.read().then(readChunk)
            return
          }
          if (commentPhase) {
            commentMD += decoder.decode(value)
            document.getElementById("analysis-comment").innerHTML +=
              decoder.decode(value)
            // 改行が起きる時にMarkdownをHTMLに変換
            if (decoder.decode(value).indexOf("\n") !== -1) {
              document.getElementById("analysis-comment").innerHTML =
                md2html(commentMD)
            }
          } else {
            document.getElementById("analysis-news").innerHTML =
              decoder.decode(value)
          }

          reader.read().then(readChunk)
        }
        reader.read().then(readChunk)
      })
  })
  document.getElementById("next-button").addEventListener("click", () => {
    if (commentIndex === maxCommentIndex) {
      commentIndex = 0
    }
    commentIndex++
    updateComment()
  })
  document.getElementById("prev-button").addEventListener("click", () => {
    if (commentIndex > 0) {
      commentIndex--
      updateComment()
    }
    if (commentIndex === -1) {
      document.getElementById("prev-button").disabled = true
    }
  })
  document.getElementById("prev-button").disabled = true

  const likeButton = document.getElementById("like-button")
  const dislikeButton = document.getElementById("dislike-button")

  likeButton.addEventListener("click", () => {
    const icon = likeButton.getElementsByTagName("span")[0]
    if (icon.classList.contains("like_animation")) {
      icon.classList.remove("like_animation")
    }
    icon.offsetWidth
    icon.classList.add("like_animation")

    if (dislikeButton.classList.contains("selected")) {
      dislikeButton.classList.remove("selected")
    }
    likeButton.classList.add("selected")
    const index = randomIndices[commentIndex]
    for (let i = 0; i < preferences.length; i++) {
      if (preferences[i].id === index) {
        preferences[i].reaction = 1
        uopdateAnalysisButton()
        return
      }
    }
    preferences.push({ id: index, reaction: 1 })
    updateAnalysisButton()
  })

  document.getElementById("dislike-button").addEventListener("click", () => {
    const icon = document
      .getElementById("dislike-button")
      .getElementsByTagName("span")[0]
    if (icon.classList.contains("dislike_animation")) {
      icon.classList.remove("dislike_animation")
    }
    icon.offsetWidth
    icon.classList.add("dislike_animation")

    if (likeButton.classList.contains("selected")) {
      likeButton.classList.remove("selected")
    }
    dislikeButton.classList.add("selected")
    const index = randomIndices[commentIndex]
    for (let i = 0; i < preferences.length; i++) {
      if (preferences[i].id === index) {
        preferences[i].reaction = -1
        updateAnalysisButton()
        return
      }
    }
    preferences.push({ id: index, reaction: -1 })
    updateAnalysisButton()
  })

  document.getElementById("analysis-close-button").onclick = () => {
    document.getElementById("analysis-comment").innerHTML = ""
    document.getElementById(
      "analysis-news"
    ).innerHTML = `<div class="myLoader">Loading...</div>`
    document.getElementById("analysis-wrapper").style.display = "none"
  }
})

function clickNews(target) {
  const news_url = target.dataset.newsUrl
  window.open(news_url, "_blank")
}

function md2html(md) {
  paragraphs = md.split("\n\n")
  html = ""
  for (let i = 0; i < paragraphs.length; i++) {
    lines = paragraphs[i].split("\n")
    for (let j = 0; j < lines.length; j++) {
      if (lines[j].startsWith("...")) {
        continue
      }
      // 太字の変換
      if (lines[j].indexOf("**") !== -1 && lines[j].split("**").length === 3) {
        lines[j] = lines[j].replace("**", "<b>")
        lines[j] = lines[j].replace("**", "</b>")
      }

      // リストの変換
      if (lines[j].startsWith("- ")) {
        html += `<li>${lines[j].slice(2)}</li>`
      } else {
        html += `<p>${lines[j]}</p>`
      }
    }
    if (i !== paragraphs.length - 1) {
      html += "<br />"
    }
  }
  return html
}
