import { useAuth } from '../context/AuthContext';
import { Link } from 'react-router-dom';
import { Database, Mic, BookOpen, Users } from 'lucide-react';

export default function Dashboard() {
  const { user } = useAuth();

  const isAdmin = user?.role === 'super_admin' || user?.role === 'dealership_admin';
  
  const features = [
    // RAG Management - only for admins
    ...(isAdmin ? [{
      title: 'RAG Management',
      description: 'Upload documents and manage your knowledge base',
      icon: Database,
      link: '/rag',
      color: 'bg-blue-500',
    }] : []),
    {
      title: 'Training Mode',
      description: 'Learn from Adam Marburger\'s expertise',
      icon: BookOpen,
      link: '/voice-call?mode=training',
      color: 'bg-purple-500',
    },
    {
      title: 'Role-Play',
      description: 'Practice with AI customers',
      icon: Users,
      link: '/voice-call?mode=roleplay',
      color: 'bg-orange-500',
    },
    {
      title: 'Text Chat',
      description: 'Chat with the AI trainer via text',
      icon: Mic,
      link: '/chat',
      color: 'bg-green-500',
    },
  ];

  return (
    <div>
      <div className="mb-6 sm:mb-8">
        <h1 className="text-xl sm:text-2xl font-bold text-gray-900">
          Welcome back, {user?.first_name}!
        </h1>
        <p className="mt-1 text-sm sm:text-base text-gray-600">
          Here's an overview of your AI training platform.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 mb-6 sm:mb-8">
        {features.map((feature) => (
          <Link
            key={feature.title}
            to={feature.link}
            className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 sm:p-6 hover:shadow-md transition-shadow"
          >
            <div
              className={`w-10 h-10 sm:w-12 sm:h-12 ${feature.color} rounded-lg flex items-center justify-center mb-3 sm:mb-4`}
            >
              <feature.icon className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
            </div>
            <h3 className="text-base sm:text-lg font-semibold text-gray-900">{feature.title}</h3>
            <p className="mt-1 text-xs sm:text-sm text-gray-600">{feature.description}</p>
          </Link>
        ))}
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 sm:p-6">
        <h2 className="text-base sm:text-lg font-semibold text-gray-900 mb-4">Quick Start Guide</h2>
        <div className="space-y-4">
          <div className="flex items-start">
            <div className="flex-shrink-0 w-7 h-7 sm:w-8 sm:h-8 bg-primary-100 rounded-full flex items-center justify-center">
              <span className="text-primary-600 font-semibold text-sm sm:text-base">1</span>
            </div>
            <div className="ml-3 sm:ml-4">
              <h4 className="font-medium text-gray-900 text-sm sm:text-base">Set up your knowledge base</h4>
              <p className="text-xs sm:text-sm text-gray-600">
                Go to RAG Management and initialize your dealership's knowledge base.
              </p>
            </div>
          </div>
          <div className="flex items-start">
            <div className="flex-shrink-0 w-7 h-7 sm:w-8 sm:h-8 bg-primary-100 rounded-full flex items-center justify-center">
              <span className="text-primary-600 font-semibold text-sm sm:text-base">2</span>
            </div>
            <div className="ml-3 sm:ml-4">
              <h4 className="font-medium text-gray-900 text-sm sm:text-base">Upload training materials</h4>
              <p className="text-xs sm:text-sm text-gray-600">
                Upload PDFs, documents, and other training materials to different topics.
              </p>
            </div>
          </div>
          <div className="flex items-start">
            <div className="flex-shrink-0 w-7 h-7 sm:w-8 sm:h-8 bg-primary-100 rounded-full flex items-center justify-center">
              <span className="text-primary-600 font-semibold text-sm sm:text-base">3</span>
            </div>
            <div className="ml-3 sm:ml-4">
              <h4 className="font-medium text-gray-900 text-sm sm:text-base">Start voice training</h4>
              <p className="text-xs sm:text-sm text-gray-600">
                Use Voice Chat to have conversations with the AI trainer or practice role-play.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
