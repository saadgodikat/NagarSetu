import { useEffect, useState } from 'react'
import {
  View, Text, ScrollView, TouchableOpacity, TextInput,
  StyleSheet, SafeAreaView, Linking, Alert, ActivityIndicator
} from 'react-native'
import { useLocalSearchParams, Stack } from 'expo-router'
import * as ImagePicker from 'expo-image-picker'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/lib/auth'
import { apiFetch, getApiBaseUrl } from '@/lib/api'
import { Assignment } from '@/lib/types'

const NEXT_STATUS: Record<string, string> = {
  assigned: 'in_progress',
  in_progress: 'resolution_submitted',
}

const NEXT_LABEL: Record<string, string> = {
  assigned: 'worker.inProgress',
  in_progress: 'worker.submitResolution',
}

export default function WorkerTaskDetail() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const { t } = useTranslation()
  const { token } = useAuth()
  const [task, setTask] = useState<Assignment | null>(null)
  const [note, setNote] = useState('')
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [photoUploaded, setPhotoUploaded] = useState(false)

  async function load() {
    if (!token || !id) return
    try {
      const data = await apiFetch<Assignment>(`/api/v1/worker/complaints/${id}`, token)
      setTask(data)
      if (data.notes) setNote(data.notes)
    } catch (err) {
      console.error(err)
    }
  }

  useEffect(() => {
    load().finally(() => setLoading(false))
  }, [token, id])

  async function advanceStatus() {
    if (!task || !token) return
    const next = NEXT_STATUS[task.status]
    if (!next) return

    if (next === 'resolution_submitted' && !photoUploaded) {
      Alert.alert('Photo Required', 'Please upload a resolution photo first before submitting resolution.')
      return
    }

    setActionLoading(true)
    try {
      const updated = await apiFetch<Assignment>(`/api/v1/worker/complaints/${id}/status?status=${next}`, token, {
        method: 'PATCH',
      })
      setTask(updated)
      if (note.trim()) {
        await apiFetch(`/api/v1/worker/complaints/${id}/notes`, token, {
          method: 'POST',
          body: JSON.stringify({ note: note.trim() }),
        })
      }
      Alert.alert('Status Updated', `Task moved to ${next.replace('_', ' ')}`)
    } catch (e) {
      Alert.alert('Error', e instanceof Error ? e.message : t('error.generic'))
    } finally {
      setActionLoading(false)
    }
  }

  async function uploadPhoto() {
    const result = await ImagePicker.launchCameraAsync({ quality: 0.7 })
    if (result.canceled || !task) return
    try {
      const form = new FormData()
      const filename = result.assets[0].uri.split('/').pop() ?? 'photo.jpg'
      const ext = filename.split('.').pop()?.toLowerCase() ?? 'jpg'
      const mimeType = ext === 'png' ? 'image/png' : 'image/jpeg'
      form.append('photo', { uri: result.assets[0].uri, name: filename, type: mimeType } as any)

      const res = await fetch(`${getApiBaseUrl()}/api/v1/worker/complaints/${task.id}/resolution-photo`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      })
      if (!res.ok) throw new Error(await res.text())
      setPhotoUploaded(true)
      Alert.alert('Success', 'Resolution photo uploaded successfully.')
    } catch (e) {
      Alert.alert('Upload Failed', e instanceof Error ? e.message : t('error.generic'))
    }
  }

  if (loading || !task) {
    return (
      <SafeAreaView style={s.center}>
        <ActivityIndicator size="large" color="#2563eb" />
      </SafeAreaView>
    )
  }

  const nextAction = NEXT_STATUS[task.status]
  const nextLabel = NEXT_LABEL[task.status]

  return (
    <SafeAreaView style={s.container}>
      <Stack.Screen options={{ title: 'Task Details' }} />
      <ScrollView contentContainerStyle={s.scroll}>
        <View style={s.header}>
          <Text style={s.title}>{task.complaint_title || `Assignment #${task.id.slice(0, 8)}`}</Text>
          <View style={s.badge}>
            <Text style={s.badgeText}>{t(`status.${task.status}`, task.status.replace('_', ' '))}</Text>
          </View>
        </View>

        {task.location_lat && task.location_lng && (
          <TouchableOpacity
            style={[s.btn, s.btnSecondary]}
            onPress={() => {
              const url = `https://maps.google.com/?q=${task.location_lat},${task.location_lng}`
              Linking.openURL(url)
            }}
          >
            <Text style={s.btnSecondaryText}>{t('worker.navigate')}</Text>
          </TouchableOpacity>
        )}

        <View style={s.card}>
          <Text style={s.label}>{t('worker.addNote')}</Text>
          <TextInput
            style={s.textarea}
            multiline
            numberOfLines={3}
            value={note}
            onChangeText={setNote}
            placeholder="Field notes, status or materials needed..."
            placeholderTextColor="#9ca3af"
          />
        </View>

        {task.status === 'in_progress' && (
          <View style={s.btnRow}>
            <TouchableOpacity style={[s.btn, s.btnSecondary, { flex: 1 }]} onPress={uploadPhoto}>
              <Text style={s.btnSecondaryText}>
                {photoUploaded ? 'Resolution Photo Uploaded (Tap to Replace)' : t('worker.uploadResolution')}
              </Text>
            </TouchableOpacity>
          </View>
        )}

        {nextAction && (
          <TouchableOpacity style={s.btn} onPress={advanceStatus} disabled={actionLoading}>
            {actionLoading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={s.btnText}>{t(nextLabel)}</Text>
            )}
          </TouchableOpacity>
        )}

        <TouchableOpacity
          style={[s.btn, s.btnDanger]}
          onPress={() =>
            Alert.alert(t('worker.requestSupport'), 'Request escalation/support from officer?', [
              { text: 'Cancel', style: 'cancel' },
              {
                text: 'Request',
                onPress: () =>
                  apiFetch(`/api/v1/worker/complaints/${id}/support-requests`, token, {
                    method: 'POST',
                    body: JSON.stringify({ description: note || 'Field worker requested assistance' }),
                  })
                    .then(() => Alert.alert('Sent', 'Support request notified to supervisor.'))
                    .catch(() => Alert.alert('Error', 'Unable to send request.')),
              },
            ])
          }
        >
          <Text style={s.btnText}>{t('worker.requestSupport')}</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  )
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f9fafb' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  scroll: { padding: 16, gap: 14 },
  header: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.03,
    shadowRadius: 4,
    elevation: 1,
  },
  title: { fontSize: 16, fontWeight: '700', color: '#111827', flex: 1, marginRight: 8 },
  badge: {
    backgroundColor: '#eff6ff',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  badgeText: { fontSize: 12, color: '#1d4ed8', fontWeight: '700', textTransform: 'uppercase' },
  card: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOpacity: 0.03,
    shadowRadius: 4,
    elevation: 1,
  },
  label: { fontSize: 13, fontWeight: '600', color: '#374151', marginBottom: 6 },
  textarea: {
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 8,
    padding: 10,
    fontSize: 14,
    minHeight: 80,
    textAlignVertical: 'top',
    backgroundColor: '#f9fafb',
    color: '#111827',
  },
  btnRow: { flexDirection: 'row', gap: 10 },
  btn: { backgroundColor: '#2563eb', borderRadius: 10, padding: 14, alignItems: 'center' },
  btnText: { color: '#fff', fontWeight: '600', fontSize: 14 },
  btnSecondary: { backgroundColor: '#fff', borderWidth: 1, borderColor: '#d1d5db' },
  btnSecondaryText: { color: '#374151', fontWeight: '600', fontSize: 13 },
  btnDanger: { backgroundColor: '#dc2626', marginTop: 8 },
})
