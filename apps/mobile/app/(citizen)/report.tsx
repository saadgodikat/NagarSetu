import { useState } from 'react'
import {
  View, Text, TouchableOpacity, TextInput, ScrollView,
  StyleSheet, SafeAreaView, ActivityIndicator, Image, Alert,
} from 'react-native'
import * as ImagePicker from 'expo-image-picker'
import * as Location from 'expo-location'
import { useRouter } from 'expo-router'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/lib/auth'
import { AiClassifyResult } from '@/lib/types'
import { getApiBaseUrl } from '@/lib/api'

const CATEGORIES = [
  'pothole',
  'garbage',
  'drainage',
  'streetlight',
  'water_leakage',
  'other',
]

type GpsStatus = 'idle' | 'capturing' | 'done'

export default function ReportScreen() {
  const { t } = useTranslation()
  const { token } = useAuth()
  const router = useRouter()

  const [step, setStep] = useState(1)
  const [photo, setPhoto] = useState<{ uri: string } | null>(null)
  const [aiSuggestion, setAiSuggestion] = useState<AiClassifyResult | null>(null)
  const [category, setCategory] = useState('')
  const [description, setDescription] = useState('')
  const [gpsStatus, setGpsStatus] = useState<GpsStatus>('idle')
  const [location, setLocation] = useState<{ lat: number; lng: number } | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  async function pickPhoto(fromCamera: boolean) {
    const result = fromCamera
      ? await ImagePicker.launchCameraAsync({ quality: 0.7 })
      : await ImagePicker.launchImageLibraryAsync({ quality: 0.7 })

    if (!result.canceled && result.assets[0]) {
      const asset = result.assets[0]
      setPhoto({ uri: asset.uri })
      // Try AI classification
      try {
        const form = new FormData()
        form.append('description', description || '')
        const filename = asset.uri.split('/').pop() ?? 'photo.jpg'
        const ext = filename.split('.').pop()?.toLowerCase() ?? 'jpg'
        const mimeType = ext === 'png' ? 'image/png' : 'image/jpeg'
        form.append('photo', { uri: asset.uri, name: filename, type: mimeType } as any)
        const res = await fetch(`${getApiBaseUrl()}/api/v1/complaints/ai/classify`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
          body: form,
        })
        if (res.ok) {
          const data: AiClassifyResult = await res.json()
          setAiSuggestion(data)
          if (data.category) setCategory(data.category)
        }
      } catch { /* classification is optional */ }
    }
  }

  async function captureGps() {
    setGpsStatus('capturing')
    const { status } = await Location.requestForegroundPermissionsAsync()
    if (status !== 'granted') {
      setGpsStatus('idle')
      Alert.alert('Permission denied', 'Location access is needed to pinpoint the issue.')
      return
    }
    const loc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High })
    setLocation({ lat: loc.coords.latitude, lng: loc.coords.longitude })
    setGpsStatus('done')
  }

  async function handleSubmit() {
    if (!token) return
    if (!photo) {
      Alert.alert('Photo required', 'Attach a photo before submitting.')
      return
    }
    setSubmitting(true)
    try {
      const form = new FormData()
      form.append('title', description || category || 'Complaint')
      form.append('description', description || category || 'Complaint')
      const lat = location ? location.lat : 17.6868
      const lng = location ? location.lng : 75.9011
      form.append('latitude', String(lat))
      const filename = photo.uri.split('/').pop() ?? 'photo.jpg'
      const ext = filename.split('.').pop()?.toLowerCase() ?? 'jpg'
      const mimeType = ext === 'png' ? 'image/png' : 'image/jpeg'
      form.append('photo', { uri: photo.uri, name: filename, type: mimeType } as any)
      if (category) {
        form.append('category', category)
      }

      const res = await fetch(`${getApiBaseUrl()}/api/v1/complaints`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      })
      if (!res.ok) throw new Error(await res.text())
      setSubmitted(true)
      setTimeout(() => router.replace('/(citizen)/home'), 1800)
    } catch (e) {
      Alert.alert('Error', e instanceof Error ? e.message : t('error.generic'))
    } finally {
      setSubmitting(false)
    }
  }

  if (submitted) {
    return (
      <SafeAreaView style={[s.container, { justifyContent: 'center', alignItems: 'center', padding: 24 }]}>
        <View style={s.successCircle}>
          <Text style={s.checkmarkText}>✓</Text>
        </View>
        <Text style={s.successText}>{t('report.submitted')}</Text>
      </SafeAreaView>
    )
  }

  return (
    <SafeAreaView style={s.container}>
      {/* Progress indicator */}
      <View style={s.progressRow}>
        {[1, 2, 3].map((n) => (
          <View key={n} style={[s.progressDot, step >= n && s.progressActive, n === step && s.progressCurrent]} />
        ))}
      </View>
      <Text style={s.stepLabel}>{t(`report.step${step}`)} ({step}/3)</Text>

      <ScrollView contentContainerStyle={s.scroll} keyboardShouldPersistTaps="handled">

        {/* Step 1: Photo */}
        {step === 1 && (
          <View style={s.section}>
            {photo ? (
              <Image source={{ uri: photo.uri }} style={s.preview} />
            ) : (
              <View style={s.photoPlaceholder}>
                <Text style={s.photoPlaceholderText}>{t('report.takePhoto')}</Text>
              </View>
            )}
            {aiSuggestion && (
              <View style={s.aiBox}>
                <Text style={s.aiLabel}>{t('report.aiSuggestion')}: {aiSuggestion.category}</Text>
                <Text style={s.aiSub}>{Math.round(aiSuggestion.confidence * 100)}% confidence</Text>
              </View>
            )}
            <TouchableOpacity style={s.btn} onPress={() => pickPhoto(true)}>
              <Text style={s.btnText}>{t('report.takePhoto')}</Text>
            </TouchableOpacity>
            <TouchableOpacity style={s.btnSecondary} onPress={() => pickPhoto(false)}>
              <Text style={s.btnSecondaryText}>{t('report.chooseGallery')}</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Step 2: Describe */}
        {step === 2 && (
          <View style={s.section}>
            <Text style={s.heading}>{t('report.category')}</Text>
            <View style={s.categoryGrid}>
              {CATEGORIES.map((cat) => (
                <TouchableOpacity
                  key={cat}
                  style={[s.catBtn, category === cat && s.catBtnActive]}
                  onPress={() => setCategory(cat)}
                >
                  <Text style={[s.catBtnText, category === cat && s.catBtnTextActive]}>
                    {t(`category.${cat}`, cat)}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <Text style={[s.heading, { marginTop: 16 }]}>{t('report.description')}</Text>
            <TextInput
              style={s.textarea}
              multiline
              numberOfLines={4}
              value={description}
              onChangeText={setDescription}
              placeholder={t('report.descriptionPlaceholder')}
              placeholderTextColor="#9ca3af"
            />

            <TouchableOpacity
              style={[s.btnSecondary, gpsStatus === 'done' && s.btnSuccess]}
              onPress={captureGps}
            >
              <Text style={s.btnSecondaryText}>
                {gpsStatus === 'capturing'
                  ? t('report.gpsCapturing')
                  : gpsStatus === 'done'
                  ? t('report.gpsReady')
                  : 'Capture GPS Location'}
              </Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Step 3: Review */}
        {step === 3 && (
          <View style={s.section}>
            <Text style={s.heading}>{t('report.step3')}</Text>
            {photo && <Image source={{ uri: photo.uri }} style={s.preview} />}
            <View style={s.reviewRow}>
              <Text style={s.reviewLabel}>Category</Text>
              <Text style={s.reviewValue}>
                {category ? t(`category.${category}`, category) : '—'}
              </Text>
            </View>
            {description ? (
              <View style={s.reviewRow}>
                <Text style={s.reviewLabel}>Description</Text>
                <Text style={s.reviewValue}>{description}</Text>
              </View>
            ) : null}
            <View style={s.reviewRow}>
              <Text style={s.reviewLabel}>GPS</Text>
              <Text style={s.reviewValue}>
                {location
                  ? `${location.lat.toFixed(4)}, ${location.lng.toFixed(4)}`
                  : 'Not captured'}
              </Text>
            </View>

            <TouchableOpacity style={s.btn} onPress={handleSubmit} disabled={submitting}>
              {submitting ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={s.btnText}>{t('report.submit')}</Text>
              )}
            </TouchableOpacity>
          </View>
        )}
      </ScrollView>

      {/* Navigation buttons */}
      <View style={s.navRow}>
        {step > 1 && (
          <TouchableOpacity style={s.navBtn} onPress={() => setStep((s) => s - 1)}>
            <Text style={s.navBtnText}>{t('report.back')}</Text>
          </TouchableOpacity>
        )}
        {step < 3 ? (
          <TouchableOpacity
            style={[s.navBtn, s.navBtnPrimary, { marginLeft: 'auto' }]}
            onPress={() => setStep((s) => s + 1)}
          >
            <Text style={[s.navBtnText, { color: '#fff' }]}>{t('report.next')}</Text>
          </TouchableOpacity>
        ) : (
          <TouchableOpacity
            style={[s.navBtn, s.navBtnPrimary, { marginLeft: 'auto' }]}
            onPress={handleSubmit}
            disabled={submitting}
          >
            {submitting ? (
              <ActivityIndicator color="#fff" size="small" />
            ) : (
              <Text style={[s.navBtnText, { color: '#fff' }]}>{t('report.submit')}</Text>
            )}
          </TouchableOpacity>
        )}
      </View>
    </SafeAreaView>
  )
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f9fafb' },
  progressRow: { flexDirection: 'row', gap: 8, justifyContent: 'center', paddingTop: 16 },
  progressDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#d1d5db' },
  progressActive: { backgroundColor: '#93c5fd' },
  progressCurrent: { backgroundColor: '#2563eb', width: 24 },
  stepLabel: { textAlign: 'center', fontSize: 12, color: '#6b7280', marginTop: 6, marginBottom: 4 },
  scroll: { padding: 20, gap: 14 },
  section: { gap: 12 },
  heading: { fontSize: 15, fontWeight: '600', color: '#111827' },
  preview: { width: '100%', height: 220, borderRadius: 14, resizeMode: 'cover' },
  photoPlaceholder: {
    width: '100%',
    height: 180,
    borderRadius: 14,
    backgroundColor: '#f3f4f6',
    borderWidth: 2,
    borderColor: '#e5e7eb',
    borderStyle: 'dashed',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 8,
  },
  photoPlaceholderText: { fontSize: 14, color: '#9ca3af' },
  aiBox: { backgroundColor: '#eff6ff', borderRadius: 10, padding: 12, gap: 2 },
  aiLabel: { fontSize: 13, color: '#1d4ed8', fontWeight: '600' },
  aiSub: { fontSize: 12, color: '#3b82f6' },
  btn: { backgroundColor: '#2563eb', borderRadius: 12, padding: 15, alignItems: 'center' },
  btnText: { color: '#fff', fontWeight: '700', fontSize: 15 },
  btnSecondary: {
    backgroundColor: '#f3f4f6',
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 12,
    padding: 13,
    alignItems: 'center',
  },
  btnSecondaryText: { color: '#374151', fontWeight: '500', fontSize: 14 },
  btnSuccess: { backgroundColor: '#dcfce7', borderColor: '#86efac' },
  categoryGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  catBtn: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 100,
    borderWidth: 1,
    borderColor: '#d1d5db',
    backgroundColor: '#fff',
  },
  catBtnActive: { backgroundColor: '#2563eb', borderColor: '#2563eb' },
  catBtnText: { fontSize: 13, color: '#374151' },
  catBtnTextActive: { color: '#fff', fontWeight: '600' },
  textarea: {
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 12,
    padding: 12,
    fontSize: 14,
    minHeight: 100,
    textAlignVertical: 'top',
    backgroundColor: '#fff',
    color: '#111827',
  },
  reviewRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6, borderBottomWidth: 1, borderColor: '#f3f4f6' },
  reviewLabel: { fontSize: 13, color: '#6b7280' },
  reviewValue: { fontSize: 13, color: '#111827', fontWeight: '600', flex: 1, textAlign: 'right' },
  successText: { fontSize: 18, fontWeight: '700', color: '#16a34a', marginTop: 16 },
  successCircle: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#dcfce7',
    borderWidth: 2,
    borderColor: '#16a34a',
    justifyContent: 'center',
    alignItems: 'center',
  },
  checkmarkText: { fontSize: 32, color: '#16a34a', fontWeight: 'bold' },
  navRow: {
    flexDirection: 'row',
    padding: 16,
    borderTopWidth: 1,
    borderColor: '#e5e7eb',
    backgroundColor: '#fff',
  },
  navBtn: {
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#d1d5db',
  },
  navBtnPrimary: { backgroundColor: '#2563eb', borderColor: '#2563eb' },
  navBtnText: { fontSize: 14, fontWeight: '600', color: '#374151' },
})
