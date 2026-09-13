import { Tabs } from 'expo-router'
import { useTranslation } from 'react-i18next'
import { Ionicons } from '@expo/vector-icons'

export default function WorkerLayout() {
  const { t } = useTranslation()
  return (
    <Tabs screenOptions={{ headerShown: true, tabBarActiveTintColor: '#2563eb' }}>
      <Tabs.Screen
        name="tasks"
        options={{
          title: t('worker.myTasks'),
          tabBarIcon: ({ color }) => <Ionicons name="clipboard-outline" size={22} color={color} />,
        }}
      />
      <Tabs.Screen name="task/[id]" options={{ href: null }} />
    </Tabs>
  )
}
