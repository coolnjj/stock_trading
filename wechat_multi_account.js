// OpenClaw 微信多账号分发脚本
// 配置你的两个微信账号ID（实际使用时替换成你自己的ID）
const ACCOUNT_CONFIG = {
  "wxid_xxxxxx1": { // 第一个微信的ID
    name: "主号",
    allowCommands: ["*"], // 允许所有命令
    autoReply: true,
    memoryScope: "main" // 用主会话记忆
  },
  "wxid_xxxxxx2": { // 第二个微信的ID
    name: "副号",
    allowCommands: ["stock", "search", "summary"], // 只允许股票、搜索、摘要功能
    autoReply: true,
    memoryScope: "secondary" // 独立记忆空间
  }
};

// 消息处理逻辑
async function handleWechatMessage(msg) {
  const fromAccount = msg.from_wxid || msg.channel_id;
  const account = ACCOUNT_CONFIG[fromAccount];
  
  if (!account) {
    // 未知账号直接拒绝
    return { text: "抱歉，未授权的账号无法使用服务。", reply: false };
  }

  // 权限校验
  if (account.allowCommands !== "*" && !account.allowCommands.some(cmd => msg.content.includes(cmd))) {
    return { text: `抱歉，当前账号仅允许使用以下功能：${account.allowCommands.join("、")}`, reply: true };
  }

  // 绑定记忆空间
  process.env.MEMORY_SCOPE = account.memoryScope;
  console.log(`收到来自【${account.name}】的消息：${msg.content}`);

  // 正常交给OpenClaw处理
  return {
    process: true,
    replyPrefix: `【${account.name}】\n` // 回复时带上账号标识，避免混淆
  };
}

module.exports = handleWechatMessage;
