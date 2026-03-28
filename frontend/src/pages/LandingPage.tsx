import React from "react";
import { Link, Navigate } from "react-router-dom";
import { 
  BrainCircuit, 
  Library, 
  Sparkles, 
  Upload, 
  LayoutDashboard, 
  Zap, 
  CheckCircle,
  ArrowRight,
  FileCheck2,
  Briefcase
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

export function LandingPage() {
  const { user, token, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-brand-background dark:bg-[#0B0F19] flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-4 border-slate-200 dark:border-slate-800 border-t-brand-primary animate-spin" />
      </div>
    );
  }

  // Redirect authenticated users
  if (user || token) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="min-h-screen bg-brand-background dark:bg-[#0B0F19] text-brand-text dark:text-slate-200 selection:bg-brand-primary/20 transition-colors duration-300">
      
      {/* 1. Header & Hero Section */}
      <header className="container mx-auto px-6 py-6 flex justify-between items-center max-w-7xl">
        <div className="flex items-center gap-2">
          <div className="bg-brand-primary p-2 rounded-xl text-white">
            <BrainCircuit size={24} />
          </div>
          <span className="text-xl font-heading font-bold text-slate-900 dark:text-white">AI Job Analyzer</span>
        </div>
        <div className="hidden sm:flex items-center gap-4">
          <Link to="/login" className="px-4 py-2 font-medium hover:text-brand-primary transition-colors cursor-pointer">Log In</Link>
          <Link to="/register" className="bg-brand-cta text-white px-5 py-2.5 rounded-xl font-medium shadow-sm hover:opacity-90 hover:-translate-y-0.5 transition-all text-sm cursor-pointer">
            Sign Up Free
          </Link>
        </div>
      </header>

      <main>
        {/* Hero */}
        <section className="relative px-6 pt-20 pb-32 max-w-7xl mx-auto text-center">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-brand-primary/10 dark:bg-brand-secondary/5 blur-[120px] rounded-full point-events-none -z-10" />
          
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 dark:bg-blue-900/30 text-brand-primary dark:text-blue-400 text-sm font-medium mb-8 border border-blue-100 dark:border-blue-800/50">
            <Sparkles size={16} />
            <span>Elevate your job application game</span>
          </div>
          
          <h1 className="text-5xl md:text-7xl font-heading font-bold tracking-tight text-slate-900 dark:text-white mb-6 leading-[1.1]">
            Match your CV to <br className="hidden md:block"/> the perfect job.
          </h1>
          
          <p className="text-lg md:text-xl text-slate-600 dark:text-slate-400 mb-10 max-w-2xl mx-auto">
            Analyze job descriptions, manage your CV library, and let AI choose the best match so you can apply with confidence.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <Link to="/register" className="w-full sm:w-auto px-8 py-3.5 bg-brand-cta text-white text-base font-semibold rounded-xl shadow-[0_4px_12px_rgba(34,197,94,0.25)] hover:shadow-[0_6px_16px_rgba(34,197,94,0.35)] hover:-translate-y-0.5 transition-all flex items-center justify-center gap-2 cursor-pointer">
              Get Started for Free <ArrowRight size={18} />
            </Link>
            <Link to="/login" className="w-full sm:w-auto px-8 py-3.5 bg-white dark:bg-[#151B2B] text-slate-700 dark:text-slate-300 font-semibold rounded-xl border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 hover:bg-slate-50 dark:hover:bg-[#1A2235] transition-all cursor-pointer shadow-sm">
              Log In
            </Link>
          </div>
        </section>

        {/* 2. Features Section */}
        <section className="py-24 bg-white/50 dark:bg-[#111726]/50 border-y border-slate-200/50 dark:border-slate-800/50">
          <div className="max-w-7xl mx-auto px-6">
            <div className="text-center mb-16">
              <h2 className="text-3xl font-heading font-bold text-slate-900 dark:text-white mb-4">Everything you need to land the job</h2>
              <p className="text-slate-600 dark:text-slate-400 max-w-2xl mx-auto">Powerful tools designed to simplify your application process and highlight your true potential.</p>
            </div>
            
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[
                { icon: BrainCircuit, title: "AI Job Analysis", desc: "Instantly break down complex job descriptions into core requirements." },
                { icon: Library, title: "CV Library", desc: "Store and organize all your customized resumes in one secure place." },
                { icon: Sparkles, title: "Smart Matching", desc: "Let AI evaluate your CVs and recommend the best one for any job." },
                { icon: Upload, title: "Multiple Uploads", desc: "Upload multiple CVs at once and build your library in seconds." },
                { icon: LayoutDashboard, title: "Personal Dashboard", desc: "Track all your analyses, jobs, and CV matches in a clean dashboard." },
                { icon: Zap, title: "Fast & Lightweight", desc: "Lightning-fast processing so you can apply to jobs without delay." },
              ].map((feature, idx) => (
                <div key={idx} className="glass-card-solid p-6 rounded-2xl interactive-card">
                  <div className="w-12 h-12 rounded-xl bg-brand-background dark:bg-slate-800/80 flex items-center justify-center text-brand-primary dark:text-brand-secondary mb-4">
                    <feature.icon size={24} />
                  </div>
                  <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">{feature.title}</h3>
                  <p className="text-slate-600 dark:text-slate-400 text-sm leading-relaxed">{feature.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* 3. How it Works */}
        <section className="py-24 max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-heading font-bold text-slate-900 dark:text-white mb-4">How it works</h2>
            <p className="text-slate-600 dark:text-slate-400">Three simple steps to your next interview.</p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8 relative">
            <div className="hidden md:block absolute top-[40px] left-[15%] right-[15%] h-0.5 bg-gradient-to-r from-brand-primary/10 via-brand-primary/30 to-brand-primary/10 dark:from-slate-800 dark:via-brand-secondary/30 dark:to-slate-800 z-0"/>
            
            {[
              { num: 1, icon: Upload, title: "Upload your CVs", desc: "Drop your resumes into your personal library." },
              { num: 2, icon: Briefcase, title: "Paste a job description", desc: "Add the details of the position you want." },
              { num: 3, icon: FileCheck2, title: "Get the best match", desc: "Our AI tells you exactly which CV to use." },
            ].map((step, idx) => (
              <div key={idx} className="relative z-10 flex flex-col items-center text-center">
                <div className="w-16 h-16 rounded-full bg-white dark:bg-[#151B2B] border-4 border-brand-background dark:border-[#0B0F19] shadow-lg flex items-center justify-center text-brand-primary dark:text-brand-secondary font-bold text-xl mb-6">
                  {step.num}
                </div>
                <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-3">{step.title}</h3>
                <p className="text-slate-600 dark:text-slate-400">{step.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* 4. Why this product */}
        <section className="py-24 bg-brand-primary text-white">
          <div className="max-w-7xl mx-auto px-6">
            <div className="grid md:grid-cols-2 gap-12 items-center">
              <div>
                <h2 className="text-3xl md:text-4xl font-heading font-bold mb-6">Why use AI Job Analyzer?</h2>
                <p className="text-blue-100 text-lg mb-8 leading-relaxed">
                  The modern job market requires tailoring your application to each company. We automate the heavy lifting so you can focus on the interview.
                </p>
                <ul className="space-y-4">
                  {[
                    "Save hours of time analyzing roles",
                    "Choose the right CV instantly",
                    "Increase your callback rate",
                    "Keep job applications organized"
                  ].map((benefit, idx) => (
                    <li key={idx} className="flex items-center gap-3">
                      <CheckCircle className="text-brand-cta" size={20} />
                      <span className="font-medium">{benefit}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="relative">
                 {/* Visual placeholder using a stylized glass card approach */}
                 <div className="rounded-2xl bg-white/10 border border-white/20 p-6 backdrop-blur-md shadow-2xl relative z-10">
                    <div className="flex justify-between items-center border-b border-white/10 pb-4 mb-4">
                      <div className="flex gap-2">
                        <div className="w-3 h-3 rounded-full bg-red-400"/>
                        <div className="w-3 h-3 rounded-full bg-amber-400"/>
                        <div className="w-3 h-3 rounded-full bg-brand-cta"/>
                      </div>
                      <div className="h-4 w-24 bg-white/20 rounded-full" />
                    </div>
                    <div className="space-y-4">
                      <div className="h-6 w-3/4 bg-white/20 rounded-md" />
                      <div className="h-4 w-full bg-white/10 rounded-md" />
                      <div className="h-4 w-5/6 bg-white/10 rounded-md" />
                      <div className="flex gap-4 pt-4">
                        <div className="h-10 w-24 bg-brand-cta rounded-lg" />
                        <div className="h-10 w-32 bg-white/10 rounded-lg" />
                      </div>
                    </div>
                 </div>
                 {/* Decorative elements behind */}
                 <div className="absolute -top-6 -right-6 w-24 h-24 bg-brand-cta/40 rounded-full blur-2xl z-0" />
                 <div className="absolute -bottom-8 -left-8 w-32 h-32 bg-blue-400/30 rounded-full blur-2xl z-0" />
              </div>
            </div>
          </div>
        </section>

        {/* 5. Bottom CTA */}
        <section className="py-24 text-center px-6 max-w-4xl mx-auto">
          <h2 className="text-3xl md:text-5xl font-heading font-bold text-slate-900 dark:text-white mb-6">
            Ready to find your match?
          </h2>
          <p className="text-xl text-slate-600 dark:text-slate-400 mb-10">
            Start optimizing your job applications today. It takes less than a minute to sign up.
          </p>
          <Link to="/register" className="inline-flex items-center gap-2 px-8 py-4 bg-brand-cta text-white font-bold rounded-xl shadow-lg hover:-translate-y-1 hover:shadow-xl transition-all cursor-pointer">
            Create Your Free Account <ArrowRight size={20} />
          </Link>
        </section>
      </main>

      {/* 6. Footer */}
      <footer className="border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0B0F19]">
        <div className="max-w-7xl mx-auto px-6 py-12 flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-2">
            <BrainCircuit className="text-brand-primary dark:text-brand-secondary" size={24} />
            <span className="font-heading font-bold text-slate-900 dark:text-white">AI Job Analyzer</span>
          </div>
          <p className="text-slate-500 dark:text-slate-500 text-sm">
            © {new Date().getFullYear()} AI Job Analyzer. All rights reserved.
          </p>
          <div className="flex gap-6">
            <Link to="/login" className="text-sm font-medium text-slate-500 hover:text-brand-primary transition-colors">Log In</Link>
            <Link to="/register" className="text-sm font-medium text-slate-500 hover:text-brand-primary transition-colors">Register</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
