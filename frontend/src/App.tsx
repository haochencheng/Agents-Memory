import { Routes, Route } from 'react-router-dom'
import RootLayout from '@/layouts/RootLayout'
import Overview from '@/pages/dashboard/Overview'
import ProjectList from '@/pages/dashboard/ProjectList'
import ProjectDetail from '@/pages/dashboard/ProjectDetail'
import MemoryRecords from '@/pages/dashboard/MemoryRecords'
import Workflow from '@/pages/dashboard/Workflow'
import Checks from '@/pages/dashboard/Checks'
import Scheduler from '@/pages/dashboard/Scheduler'
import WikiHome from '@/pages/wiki/WikiHome'
import TopicDetail from '@/pages/wiki/TopicDetail'
import TopicEdit from '@/pages/wiki/TopicEdit'
import KnowledgeGraphPage from '@/pages/wiki/KnowledgeGraphPage'
import LintReport from '@/pages/wiki/LintReport'
import Ingest from '@/pages/wiki/Ingest'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<RootLayout />}>
        <Route index element={<Overview />} />
        <Route path="projects" element={<ProjectList />} />
        <Route path="projects/:id" element={<ProjectDetail />} />
        <Route path="memory" element={<MemoryRecords />} />
        <Route path="workflow" element={<Workflow />} />
        <Route path="checks" element={<Checks />} />
        <Route path="scheduler" element={<Scheduler />} />
        <Route path="wiki" element={<WikiHome />} />
        <Route path="wiki/graph" element={<KnowledgeGraphPage />} />
        <Route path="wiki/lint" element={<LintReport />} />
        <Route path="wiki/ingest" element={<Ingest />} />
        <Route path="wiki/:topic" element={<TopicDetail />} />
        <Route path="wiki/:topic/edit" element={<TopicEdit />} />
      </Route>
    </Routes>
  )
}
