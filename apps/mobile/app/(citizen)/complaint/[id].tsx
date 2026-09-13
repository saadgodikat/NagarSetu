import { useEffect, useState } from 'react'
import {
  View, Text, ScrollView, TouchableOpacity,
  StyleSheet, SafeAreaView, Image, ActivityIndicator, Alert
} from 'react-native'
import { useLocalSearchParams, useRouter } from 'expo-router'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/lib/auth'
import { apiFetch, resolveImageUrl } from '@/lib/api'
import { ComplaintSummary, ComplaintStatus } from '@/lib/types'

const STEPS: ComplaintStatus[] = [
  'submitted',
  'under_review',
  'assigned',
  'in_progress',
  'resolution_submitted',
  'verified',
  'closed',
]

export default function CitizenComplaintDetail() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const { t } = useTranslation()
  const { token } = useAuth()
  const router = useRouter()
  const [complaint, setComplaint] = useState<ComplaintSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [confirming, setConfirming] = useState(false)

  async function load() {
    if (!token || !id) return
    try {
      const c = await apiFetch<ComplaintSummary>(`/api/v1/complaints/${id}`, token)
      setComplaint(c)
    } catch (err) {
      console.error(err)
    }
  }

  useEffect(() => {
    load().finally(() => setLoading(false))
  }, [token, id])

  async function confirmResolution(accepted: boolean) {
    if (!token || !id) return
    setConfirming(true)
    try {
      const endpoint = accepted
        ? `/api/v1/complaints/${id}/resolution/confirm`
        : `/api/v1/complaints/${id}/resolution/reject`
      const payload = accepted ? {} : { reason: 'Citizen marked issue not resolved' }
      await apiFetch(endpoint, token, {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      Alert.alert(
        accepted ? 'Thank you!' : 'Reopened',
        accepted ? 'Issue marked as resolved.' : 'Issue will be reviewed again by the team.'
      )
      await load()
    } catch (e) {
      Alert.alert('Error', e instanceof Error ? e.message : t('error.generic'))
    } finally {
      setConfirming(false)
    }
  }

  if (loading) {
    return (
      <SafeAreaView style={s.center}>
        <ActivityIndicator size="large" color="#2563eb" />
      </SafeAreaView>
    )
  }

  if (!complaint) {
    return (
      <SafeAreaView style={s.center}>
        <Text style={s.empty}>{t('error.generic')}</Text>
      </SafeAreaView>
    )
  }

  const currentStep = STEPS.indexOf(complaint.status)
  const afterPhoto = complaint.images?.find((i) => i.image_type === 'after')
  const beforePhoto = complaint.images?.find((i) => i.image_type === 'before')

  return (
    <SafeAreaView style={s.container}>
      <ScrollView contentContainerStyle={s.scroll}>
        <View style={s.header}>
          <Text style={s.title}>{complaint.title}</Text>
          <Text style={s.sub}>
            #{complaint.id.slice(0, 8)} · {complaint.category} · {new Date(complaint.created_at).toLocaleDateString()}
          </Text>
        </View>

        {complaint.description ? (
          <View style={s.card}>
            <Text style={s.desc}>{complaint.description}</Text>
          </View>
        ) : null}

        {/* Status Timeline */}
        <View style={s.card}>
          <Text style={s.cardTitle}>Status Progress</Text>
          <View style={s.timeline}>
            {STEPS.map((step, i) => {
              const isPassed = i <= currentStep
              const isCurrent = i === currentStep
              return (
                <View key={step} style={s.timelineRow}>
                  <View style={s.nodeCol}>
                    <View style={[s.dot, isPassed && s.dotPassed, isCurrent && s.dotCurrent]} />
                    {i < STEPS.length - 1 && (
                      <View style={[s.line, i < currentStep && s.linePassed]} />
                    )}
                  </View>
                  <View style={s.labelCol}>
                    <Text style={[s.stepText, isPassed && s.stepTextPassed, isCurrent && s.stepTextCurrent]}>
                      {t(`status.${step}`)}
                    </Text>
                  </View>
                </View>
              )
            })}
          </View>
        </View>

        {/* Photos */}
        {(beforePhoto || afterPhoto) && (
          <View style={s.card}>
            <Text style={s.cardTitle}>Photos</Text>
            <View style={s.photoRow}>
              {beforePhoto && (
                <View style={s.photoCol}>
                  <Text style={s.photoLabel}>Before</Text>
                  <Image source={{ uri: resolveImageUrl(beforePhoto.url) }} style={s.photo} />
                </View>
              )}
              {afterPhoto && (
                <View style={s.photoCol}>
                  <Text style={s.photoLabel}>Resolved (After)</Text>
                  <Image source={{ uri: resolveImageUrl(afterPhoto.url) }} style={s.photo} />
                </View>
              )}
            </View>
          </View>
        )}

        {/* Resolution confirmation prompt */}
        {complaint.status === 'resolution_submitted' && (
          <View style={[s.card, s.actionCard]}>
            <Text style={s.promptTitle}>{t('citizen.resolutionPrompt')}</Text>
            {confirming ? (
              <ActivityIndicator color="#2563eb" style={{ marginVertical: 12 }} />
            ) : (
              <View style={s.btnGroup}>
                <TouchableOpacity
                  style={[s.btn, s.btnSuccess]}
                  onPress={() => confirmResolution(true)}
                >
                  <Text style={s.btnText}>{t('citizen.confirmResolution')}</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[s.btn, s.btnDanger]}
                  onPress={() => confirmResolution(false)}
                >
                  <Text style={s.btnText}>{t('citizen.rejectResolution')}</Text>
                </TouchableOpacity>
              </View>
            )}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  )
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f9fafb' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  scroll: { padding: 16, gap: 14 },
  header: { marginBottom: 4 },
  title: { fontSize: 18, fontWeight: '700', color: '#111827' },
  sub: { fontSize: 13, color: '#6b7280', marginTop: 3 },
  empty: { color: '#6b7280', fontSize: 14 },
  desc: { fontSize: 14, color: '#374151', lineHeight: 20 },
  card: {
    backgroundColor: '#fff',
    borderRadius: 14,
    padding: 16,
    shadowColor: '#000',
    shadowOpacity: 0.04,
    shadowRadius: 6,
    elevation: 2,
  },
  cardTitle: { fontSize: 15, fontWeight: '600', color: '#111827', marginBottom: 14 },
  timeline: { paddingLeft: 4 },
  timelineRow: { flexDirection: 'row', minHeight: 40 },
  nodeCol: { width: 24, alignItems: 'center' },
  dot: { width: 12, height: 12, borderRadius: 6, backgroundColor: '#d1d5db', marginTop: 3 },
  dotPassed: { backgroundColor: '#93c5fd' },
  dotCurrent: { backgroundColor: '#2563eb', width: 14, height: 14, borderRadius: 7 },
  line: { width: 2, flex: 1, backgroundColor: '#e5e7eb', marginVertical: 2 },
  linePassed: { backgroundColor: '#93c5fd' },
  labelCol: { flex: 1, paddingLeft: 10, paddingBottom: 16 },
  stepText: { fontSize: 13, color: '#9ca3af' },
  stepTextPassed: { color: '#4b5563' },
  stepTextCurrent: { color: '#1d4ed8', fontWeight: '700' },
  photoRow: { flexDirection: 'row', gap: 12 },
  photoCol: { flex: 1 },
  photoLabel: { fontSize: 12, color: '#6b7280', marginBottom: 6 },
  photo: { width: '100%', height: 140, borderRadius: 8, backgroundColor: '#f3f4f6' },
  actionCard: { borderLeftWidth: 4, borderLeftColor: '#2563eb' },
  promptTitle: { fontSize: 14, fontWeight: '600', color: '#111827', marginBottom: 12 },
  btnGroup: { flexDirection: 'row', gap: 10 },
  btn: { flex: 1, paddingVertical: 12, borderRadius: 8, alignItems: 'center' },
  btnSuccess: { backgroundColor: '#16a34a' },
  btnDanger: { backgroundColor: '#dc2626' },
  btnText: { color: '#fff', fontWeight: '600', fontSize: 13 },
})
