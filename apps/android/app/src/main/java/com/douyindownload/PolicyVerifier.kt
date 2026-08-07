package com.douyindownload

import android.util.Base64
import org.bouncycastle.crypto.params.Ed25519PublicKeyParameters
import org.bouncycastle.crypto.signers.Ed25519Signer
import org.json.JSONObject

/**
 * Ed25519 策略验签（防伪造停服开关）。
 *
 * 私钥仅由作者持有（scripts/sign-policy.py + secrets/policy-private-key.pem），
 * 本公钥必须与 scripts/sign-policy.py 及其他客户端保持一致。
 * 验签失败 / 缺失签名一律视为不可信策略。
 */
object PolicyVerifier {

    private const val PUBLIC_KEY_B64 = "TfI3/szbWh13QZr/FunFipeal2vb+vkrYoazGJHf6iw="

    /** 签名内容（规范化字符串，与 scripts/sign-policy.py 及各端完全一致）。 */
    fun canonicalPolicy(policy: JSONObject): String {
        val download = policy.optJSONObject("download") ?: JSONObject()
        val enabled = download.optBoolean("enabled", true)
        return listOf(
            policy.optString("updated_at", ""),
            enabled.toString(),
            download.optString("message", ""),
            download.optString("min_version", "0.0.0"),
        ).joinToString("\n")
    }

    /** 返回 true 仅当策略携带有效的 Ed25519 签名。 */
    fun verify(policy: JSONObject): Boolean {
        val signatureB64 = policy.optString("signature", "")
        if (signatureB64.isEmpty()) return false
        return try {
            val keyBytes = Base64.decode(PUBLIC_KEY_B64, Base64.DEFAULT)
            val signatureBytes = Base64.decode(signatureB64, Base64.DEFAULT)
            val payload = canonicalPolicy(policy).toByteArray(Charsets.UTF_8)

            val publicKey = Ed25519PublicKeyParameters(keyBytes, 0)
            val signer = Ed25519Signer()
            signer.init(false, publicKey) // false = verify
            signer.update(payload, 0, payload.size)
            signer.verifySignature(signatureBytes)
        } catch (e: Exception) {
            false
        }
    }
}
