import { Tabs } from 'expo-router'
import { useTranslation } from 'react-i18next'
import { Ionicons } from '@expo/vector-icons'

export default function CitizenLayout() {
  const { t } = useTranslation()
  return (
    <Tabs screenOptions={{ headerShown: true, tabBarActiveTintColor: '#2563eb' }}>
      <Tabs.Screen
        name="home"
        options={{
          title: t('citizen.myComplaints'),
          tabBarIcon: ({ color }) => <Ionicons name="list-outline" size={22} color={color} />,
        }}
      />
      <Tabs.Screen
        name="report"
        options={{
          title: t('citizen.reportProblem'),
          tabBarIcon: ({ color }) => <Ionicons name="add-circle-outline" size={22} color={color} />,
        }}
      />
      <Tabs.Screen name="complaint/[id]" options={{ href: null }} />
    </Tabs>
  )
}
