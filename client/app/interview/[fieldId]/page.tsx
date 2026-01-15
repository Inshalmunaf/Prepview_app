'use client'

import { useParams } from 'next/navigation'
import InterviewInterface from '@/components/InterviewInterface'

export default function InterviewPage() {
  const params = useParams()
  const fieldId = params.fieldId as string

  return <InterviewInterface fieldId={fieldId} />
}

