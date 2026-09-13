import { useEffect, useState } from 'react'
import {
  View, Text, FlatList, TouchableOpacity,
  StyleSheet, SafeAreaView, RefreshControl,
} from 'react-native'
import { useRouter } from 'expo-router'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/lib/auth'
import { apiFetch } from '@/lib/api'
import { ComplaintSummary, ComplaintStatus } from '@/lib/types'

const STATUS_COLORS: Record<ComplaintStatus, string> = {
  submitted: '#3b82f6',
  under_review: '#eab308',
  assigned: '#3b82f6',
  in_progress: '#f97316',
  resolution_submitted: '#eab308',
  verified: '#22c55e',
  closed: '#22c55e',
  reopened: '#ef4444',
}

export default function CitizenHome() {
  const { t } = useTranslation()
  const { token, logout } = useAuth()
  const router = useRouter()
  const [complaints, setComplaints] = useState<ComplaintSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  async function load() {
    if (!token) return
    try {
      const r = await apiFetch<{ data: ComplaintSummary[] } | ComplaintSummary[]>(
        '/api/v1/complaints',
        token
      )
      const list = Array.isArray(r) ? r : (r as { data: ComplaintSummary[] }).data ?? []
      setComplaints(list)
    } catch (e) {
      console.error(e)
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
        <Text style={s.title}>{t('citizen.myComplaints')}</Text>
        <TouchableOpacity onPress={() => logout()}>
          <Text style={s.logoutText}>Logout</Text>
        </TouchableOpacity>
      </View>

      {loading ? (
        <Text style={s.empty}>{t('loading')}</Text>
      ) : (
        <FlatList
          data={complaints}
          keyExtractor={(c) => c.id}
          contentContainerStyle={{ padding: 16, gap: 10 }}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
          ListEmptyComponent={
            <Text style={s.empty}>{t('citizen.noComplaints')}</Text>
          }
          renderItem={({ item }) => (
            <TouchableOpacity
              style={s.card}
              onPress={() => router.push(`/(citizen)/complaint/${item.id}`)}
            >
              <View style={s.cardRow}>
                <Text style={s.cardTitle} numberOfLines={1}>{item.title}</Text>
                <View style={[s.badge, { backgroundColor: STATUS_COLORS[item.status] ?? '#6b7280' }]}>
                  <Text style={s.badgeText}>{t(`status.${item.status}`)}</Text>
                </View>
              </View>
              <Text style={s.cardSub}>
                {item.category} · {new Date(item.created_at).toLocaleDateString()}
              </Text>
            </TouchableOpacity>
          )}
        />
      )}

      {/* FAB */}
      <TouchableOpacity style={s.fab} onPress={() => router.push('/(citizen)/report')}>
        <Text style={s.fabText}>+</Text>
      </TouchableOpacity>
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
    paddingBottom: 10,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderColor: '#e5e7eb',
  },
  title: { fontSize: 20, fontWeight: '700', color: '#111827' },
  logoutText: { fontSize: 13, color: '#6b7280' },
  empty: { textAlign: 'center', color: '#9ca3af', marginTop: 48, fontSize: 14, paddingHorizontal: 32 },
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 14,
    shadowColor: '#000',
    shadowOpacity: 0.04,
    shadowRadius: 6,
    elevation: 2,
  },
  cardRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  cardTitle: { fontSize: 14, fontWeight: '600', color: '#111827', flex: 1, marginRight: 8 },
  cardSub: { fontSize: 12, color: '#6b7280', marginTop: 4 },
  badge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 100 },
  badgeText: { fontSize: 11, color: '#fff', fontWeight: '600' },
  fab: {
    position: 'absolute',
    bottom: 24,
    right: 24,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#2563eb',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#2563eb',
    shadowOpacity: 0.4,
    shadowRadius: 8,
    elevation: 6,
  },
  fabText: { color: '#fff', fontSize: 30, fontWeight: '300', marginTop: -2 },
})
