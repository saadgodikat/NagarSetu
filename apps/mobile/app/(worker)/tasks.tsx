import { useEffect, useState } from 'react'
import {
  View, Text, FlatList, TouchableOpacity,
  StyleSheet, SafeAreaView, RefreshControl
} from 'react-native'
import { useRouter } from 'expo-router'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/lib/auth'
import { apiFetch } from '@/lib/api'
import { Assignment } from '@/lib/types'

export default function WorkerTasks() {
  const { t } = useTranslation()
  const { token, logout } = useAuth()
  const router = useRouter()
  const [tasks, setTasks] = useState<Assignment[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  async function load() {
    if (!token) return
    try {
      const res = await apiFetch<{ data: Assignment[] } | Assignment[]>('/api/v1/worker/complaints', token)
      const list = Array.isArray(res) ? res : (res as { data: Assignment[] }).data ?? []
      setTasks(list)
    } catch (err) {
      console.error(err)
    }
  }

  useEffect(() => {
    load().finally(() => setLoading(false))
  }, [token])

  async function onRefresh() {
    setRefreshing(true)
    await load()
    setRefreshing(false)
  }

  return (
    <SafeAreaView style={s.container}>
      <View style={s.header}>
        <Text style={s.title}>{t('worker.myTasks')}</Text>
        <TouchableOpacity onPress={() => logout()}>
          <Text style={s.logoutText}>Logout</Text>
        </TouchableOpacity>
      </View>

      {loading ? (
        <Text style={s.empty}>{t('loading')}</Text>
      ) : (
        <FlatList
          data={tasks}
          keyExtractor={(item) => item.id}
          contentContainerStyle={{ padding: 16, gap: 12 }}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
          ListEmptyComponent={
            <Text style={s.empty}>{t('worker.noTasks')}</Text>
          }
          renderItem={({ item }) => (
            <TouchableOpacity
              style={s.card}
              onPress={() => router.push(`/(worker)/task/${item.id}`)}
            >
              <View style={s.cardHeader}>
                <Text style={s.cardTitle} numberOfLines={1}>
                  {item.complaint_title || `Task #${item.id.slice(0, 8)}`}
                </Text>
                <View style={s.badge}>
                  <Text style={s.badgeText}>{item.status}</Text>
                </View>
              </View>

              <Text style={s.subText}>
                {item.priority ? `Priority: ${item.priority} · ` : ''}
                Tap to view details & route
              </Text>
            </TouchableOpacity>
          )}
        />
      )}
    </SafeAreaView>
  )
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f9fafb' },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderColor: '#e5e7eb',
  },
  title: { fontSize: 20, fontWeight: '700', color: '#111827' },
  logoutText: { fontSize: 13, color: '#6b7280' },
  empty: { textAlign: 'center', color: '#9ca3af', marginTop: 40, fontSize: 14 },
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOpacity: 0.04,
    shadowRadius: 6,
    elevation: 2,
  },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  cardTitle: { fontSize: 15, fontWeight: '600', color: '#111827', flex: 1, marginRight: 8 },
  badge: {
    backgroundColor: '#eff6ff',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#bfdbfe',
  },
  badgeText: { fontSize: 11, color: '#1d4ed8', fontWeight: '600', textTransform: 'uppercase' },
  subText: { fontSize: 12, color: '#6b7280', marginTop: 6 },
})
