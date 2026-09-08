import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import AuthRoot from './features/auth/Auth'
import './app/styles.css'
import './app/viewport.css'

const client = new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 10000, refetchOnWindowFocus: false }, mutations: { retry: false } } })
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><QueryClientProvider client={client}><BrowserRouter><AuthRoot /></BrowserRouter></QueryClientProvider></React.StrictMode>)

