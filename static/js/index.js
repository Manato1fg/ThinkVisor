let sentComments = [] // 自分が送信したコメント
let sentCommentsEmbedded = [] // 自分が送信したコメントの埋め込みベクトル
let labels = []
for (let i = 0; i < sentences.length; i++) {
  labels.push(sentences[i]) // ラベル用に
}

let data = {
  labels: labels,
  datasets: [
    {
      label: "ユーザーの意見",
      data: embeddedData,
      borderColor: "#00000000",
      backgroundColor: colors,
      pointStyle: "circle",
      pointRadius: pointSizes,
      pointHoverRadius: hoverPointSizes,
    },
  ],
}

let config = {
  type: "scatter",
  data: data,
  options: {
    responsive: true,
    onClick: async (e) => {
      if (e.chart.tooltip.opacity === 0) {
        return
      }
      fetch(
        `/neighbors?index=${idx}&sentCommentsEmbedded=${JSON.stringify(
          sentCommentsEmbedded
        )}&sentComments=${JSON.stringify(
          sentComments
        )}&data_index=${dataIndex}`,
        {
          method: "GET",
        }
      ).then((response) => {
        if (response.ok) {
          response.json().then((d) => {
            document.getElementById("selectedComment").innerHTML =
              d["the_sentence"]
            let neighbors = d["neighbors"]
            for (let i = 0; i < neighbors.length; i++) {
              const nSentence = neighbors[i]
              document.getElementById("neighbor" + (i + 1)).innerHTML =
                nSentence
            }
            // 一番上にする
            document.getElementById("relatedComments").scrollTo(0, 0)
          })
        } else {
          console.log("Network response was not ok.")
        }
      })
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
            return "クリックしてコメントを表示"
          },
        },
      },
      zoom: {
        pan: {
          enabled: true,
          mode: "xy",
        },
        zoom: {
          wheel: {
            enabled: true,
          },
          pinch: {
            enabled: true,
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

function shortenString(sentence, length) {
  if (sentence.length > length) {
    return sentence.substring(0, length) + "..."
  } else {
    return sentence
  }
}

function resetZoom() {
  if (window.myChart) {
    window.myChart.zoomScale("x", { min: min_x, max: max_x }, "default")
    window.myChart.zoomScale("y", { min: min_y, max: max_y }, "default")
  }
}

function submitComment() {
  const comment = document.getElementById("your-comment").value
  if (comment === "") {
    return
  }
  const button = document.getElementById("submit-button")
  if (button.classList.contains("is-loading")) {
    return
  }
  button.classList.add("is-loading")
  formData = new FormData()
  formData.append("comment", comment)
  formData.append("data_index", dataIndex)
  fetch("/comment", {
    method: "POST",
    body: formData,
  }).then((response) => {
    if (response.ok) {
      response.json().then((d) => {
        sentComments.push(comment)
        sentCommentsEmbedded.push([d["x"], d["y"]])
        data.datasets[0].data.push({ x: d["x"], y: d["y"] })
        data.datasets[0].backgroundColor.push("#24c938") // 緑色
        data.datasets[0].pointRadius.push(10)
        data.datasets[0].pointHoverRadius.push(13)

        labels.push(shortenString(comment, 20))
        data.labels = labels
        config.data = data

        draw() // 再描画

        sentences.push(comment)

        bulmaToast.toast({
          message: "意見を緑色の丸でプロットしました！",
          type: "is-success",
          position: "bottom-center",
          duration: 2000,
        })
        button.classList.remove("is-loading")
      })
    } else {
      console.log("Network response was not ok.")
    }
  })
  document.getElementById("your-comment").value = ""
}

function changePage(page) {
  // ページの移動
  window.location.href = "/?data_index=" + page
}

function draw() {
  if (window.myChart.destroy) {
    window.myChart.destroy()
    window.myChart = null
  }
  const ctx = document.getElementById("myChart")
  window.myChart = new Chart(ctx, config) // 描画更新
}

let selectedComment = "まだコメントを選択していません"
let idx = -1
document.getElementById("selectedComment").innerHTML = selectedComment

document.addEventListener("DOMContentLoaded", draw)
