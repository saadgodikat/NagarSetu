import { useState } from 'react'
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  KeyboardAvoidingView, Platform, ActivityIndicator, SafeAreaView,
} from 'react-native'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/lib/auth'
import { getApiBaseUrl } from '@/lib/api'

export default function LoginScreen() {
  const { t, i18n } = useTranslation()
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleLogin() {
    if (!email || !password) return
    setError('')
    setLoading(true)
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      if (!res.ok) throw new Error(t('auth.loginFailed'))
      const body = await res.json()
      const payload = JSON.parse(atob(body.access_token.split('.')[1]))
      await login(body.access_token, {
        id: payload.sub,
        name: payload.name ?? email,
        email,
        role: payload.role,
      })
    } catch (e) {
      setError(e instanceof Error ? e.message : t('auth.loginFailed'))
    } finally {
      setLoading(false)
    }
  }

  function toggleLang() {
    const next = i18n.language === 'en' ? 'mr' : 'en'
    void i18n.changeLanguage(next)
  }

  return (
    <SafeAreaView style={s.safe}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={s.container}>
        <View style={s.card}>
          <Text style={s.appName}>{t('app.name')}</Text>

          <Text style={s.label}>{t('auth.email')}</Text>
          <TextInput
            style={s.input}
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            keyboardType="email-address"
            placeholder="officer@solapur.gov.in"
            placeholderTextColor="#9ca3af"
          />

          <Text style={s.label}>{t('auth.password')}</Text>
          <TextInput
            style={s.input}
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            placeholder="••••••••"
            placeholderTextColor="#9ca3af"
          />

          {error ? <Text style={s.error}>{error}</Text> : null}

          <TouchableOpacity style={s.btn} onPress={handleLogin} disabled={loading}>
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={s.btnText}>{t('auth.signIn')}</Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity style={s.langBtn} onPress={toggleLang}>
            <Text style={s.langBtnText}>{i18n.language === 'en' ? 'मराठी' : 'English'}</Text>
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  )
}

const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#eff6ff' },
  container: { flex: 1, justifyContent: 'center', padding: 24 },
  card: {
    backgroundColor: '#fff',
    borderRadius: 20,
    padding: 28,
    shadowColor: '#000',
    shadowOpacity: 0.08,
    shadowRadius: 16,
    elevation: 5,
  },
  appName: { fontSize: 22, fontWeight: '700', color: '#1d4ed8', marginBottom: 28, textAlign: 'center' },
  label: { fontSize: 13, color: '#374151', marginBottom: 5, fontWeight: '500' },
  input: {
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 10,
    padding: 12,
    fontSize: 14,
    marginBottom: 16,
    backgroundColor: '#f9fafb',
    color: '#111827',
  },
  error: { color: '#dc2626', fontSize: 13, marginBottom: 12, textAlign: 'center' },
  btn: {
    backgroundColor: '#2563eb',
    borderRadius: 12,
    padding: 15,
    alignItems: 'center',
    marginTop: 4,
  },
  btnText: { color: '#fff', fontWeight: '700', fontSize: 16 },
  langBtn: { marginTop: 16, alignItems: 'center' },
  langBtnText: { fontSize: 13, color: '#6b7280' },
})
