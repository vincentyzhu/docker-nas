#!/bin/sh
# ============================================================
# WUD -> 钉钉机器人通知脚本 (v4)
# - 支持 WUD Command Trigger 的 batch/simple 两种模式
# - 同时校验 HTTP 状态与钉钉 errcode
# - 仅对临时网络错误、429 和 5xx 进行有限重试
# ============================================================

node -e '
var crypto = require("crypto");
var https = require("https");

var webhook = process.env.DINGTALK_WEBHOOK;
var secret = process.env.DINGTALK_SECRET || "";
var containerJson = process.env.container_json;
var containersJson = process.env.containers_json;

function readInteger(name, fallback, min, max) {
    var raw = process.env[name];
    var value = raw === undefined || raw === "" ? fallback : Number(raw);
    if (!Number.isInteger(value) || value < min || value > max) {
        console.error("[钉钉通知] " + name + " 无效，使用默认值 " + fallback + "。");
        return fallback;
    }
    return value;
}

var maxAttempts = readInteger("DINGTALK_MAX_ATTEMPTS", 3, 1, 10);
var retryDelayMs = readInteger("DINGTALK_RETRY_DELAY_SECONDS", 5, 0, 60) * 1000;

if (!webhook) {
    console.error("[钉钉通知] 未配置 DINGTALK_WEBHOOK。");
    process.exit(1);
}

function makeError(message, retryable) {
    var error = new Error(message);
    error.retryable = retryable;
    return error;
}

// 每次尝试都重新生成时间戳和签名，避免重试时使用过期签名。
function buildUrl() {
    var target = new URL(webhook);
    if (target.protocol !== "https:") {
        throw makeError("DINGTALK_WEBHOOK 必须使用 HTTPS。", false);
    }
    if (secret) {
        var timestamp = Date.now().toString();
        var sign = crypto.createHmac("sha256", secret)
            .update(timestamp + "\n" + secret)
            .digest("base64");
        target.searchParams.set("timestamp", timestamp);
        target.searchParams.set("sign", sign);
    }
    return target;
}

function send(title, text) {
    return new Promise(function(resolve, reject) {
        var body = JSON.stringify({
            msgtype: "markdown",
            markdown: { title: title, text: text }
        });
        var target = buildUrl();

        var options = {
            hostname: target.hostname,
            port: target.port || 443,
            path: target.pathname + target.search,
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Content-Length": Buffer.byteLength(body)
            },
            timeout: 15000
        };

        // 不输出查询参数，避免 access_token 或签名进入日志。
        console.error("[钉钉通知] 正在发送至 " + target.hostname + target.pathname + "。");

        var request = https.request(options, function(response) {
            var data = "";
            response.on("data", function(chunk) { data += chunk; });
            response.on("end", function() {
                console.error("[钉钉通知] HTTP " + response.statusCode + "：" + data);

                if (response.statusCode < 200 || response.statusCode >= 300) {
                    var transientHttp = response.statusCode === 408
                        || response.statusCode === 425
                        || response.statusCode === 429
                        || response.statusCode >= 500;
                    reject(makeError("HTTP " + response.statusCode + "：" + data, transientHttp));
                    return;
                }

                var result;
                try {
                    result = JSON.parse(data);
                } catch (error) {
                    reject(makeError("钉钉返回了无法解析的响应：" + data, true));
                    return;
                }

                if (result.errcode !== 0) {
                    reject(makeError(
                        "钉钉业务错误 " + result.errcode + "：" + (result.errmsg || "未知错误"),
                        false
                    ));
                    return;
                }

                resolve(result);
            });
        });

        request.on("error", function(error) {
            reject(makeError("请求失败：" + error.message, true));
        });
        request.on("timeout", function() {
            request.destroy(makeError("请求超时（15 秒）", true));
        });
        request.write(body);
        request.end();
    });
}

function sleep(milliseconds) {
    return new Promise(function(resolve) { setTimeout(resolve, milliseconds); });
}

async function sendWithRetry(title, text) {
    for (var attempt = 1; attempt <= maxAttempts; attempt++) {
        try {
            var result = await send(title, text);
            console.error("[钉钉通知] 发送成功。");
            return result;
        } catch (error) {
            var canRetry = error.retryable === true && attempt < maxAttempts;
            if (!canRetry) {
                throw error;
            }
            console.error(
                "[钉钉通知] 第 " + attempt + "/" + maxAttempts + " 次尝试失败："
                + error.message + "；" + (retryDelayMs / 1000) + " 秒后重试。"
            );
            await sleep(retryDelayMs);
        }
    }
}

function formatContainer(container) {
    var name = container.name || container.image_name || "Unknown";
    var kind = (container.updateKind && container.updateKind.kind)
        || (container.update_kind && container.update_kind.kind)
        || "tag";
    var local = (container.updateKind && container.updateKind.localValue)
        || (container.update_kind && container.update_kind.local_value)
        || "?";
    var remote = (container.updateKind && container.updateKind.remoteValue)
        || (container.update_kind && container.update_kind.remote_value)
        || "?";
    var link = (container.result && container.result.link) || container.result_link || "";

    var line = "> **" + name + "**  \n> " + kind + " `" + local + "` -> `" + remote + "`";
    if (link) {
        line += "  \n> [查看详情](" + link + ")";
    }
    return line;
}

(async function() {
    try {
        if (containersJson) {
            var containers = JSON.parse(containersJson);
            if (!Array.isArray(containers)) {
                throw makeError("containers_json 不是数组。", false);
            }
            if (containers.length === 0) {
                console.error("[钉钉通知] 本次批量数据为空，跳过发送。");
                process.exit(0);
            }

            var count = containers.length;
            console.error("[钉钉通知] 批量模式，共 " + count + " 个容器。");
            var title = count + " 个容器有可用更新";
            var text = "## Docker 容器更新提醒\n\n共 **" + count + "** 个容器有可用更新：\n\n";
            for (var index = 0; index < containers.length; index++) {
                text += formatContainer(containers[index]) + "\n\n";
            }
            text += "---\n*via WUD*";

            await sendWithRetry(title, text);
            process.exit(0);
        }

        if (containerJson) {
            var container = JSON.parse(containerJson);
            var name = container.name || "Unknown";
            console.error("[钉钉通知] 单条模式：" + name + "。");
            var singleTitle = "Docker 更新：" + name;
            var singleText = "## Docker 容器更新提醒\n\n"
                + formatContainer(container) + "\n\n---\n*via WUD*";

            await sendWithRetry(singleTitle, singleText);
            process.exit(0);
        }

        console.error("[钉钉通知] 未收到容器更新数据，跳过发送。");
        process.exit(0);
    } catch (error) {
        console.error("[钉钉通知] 发送失败：" + error.message);
        process.exit(1);
    }
})();
'
