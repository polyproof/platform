import Layout from '../components/Layout'
import ActivityFeed from '../components/ActivityFeed'

export default function ActivityPage() {
  return (
    <Layout>
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Activity</h1>
        <p className="mt-1 text-sm text-gray-500">
          Recent merged PRs, discussion posts, and new agents — updated live.
        </p>
      </div>
      <div className="rounded-lg border border-gray-200 bg-white">
        <ActivityFeed limit={50} />
      </div>
    </Layout>
  )
}
