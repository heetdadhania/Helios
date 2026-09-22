import React from 'react';


interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'team_member';
  lastActive: string;
}

const teamMembers: TeamMember[] = [
  {
    id: 'tm_1',
    name: 'Sarah Chen',
    email: 'admin@helios.io',
    role: 'admin',
    lastActive: 'Active now',
  },
  {
    id: 'tm_2',
    name: 'David Miller',
    email: 'team@helios.io',
    role: 'team_member',
    lastActive: '25 mins ago',
  },
  {
    id: 'tm_3',
    name: 'Elena Rostova',
    email: 'elena@helios.io',
    role: 'team_member',
    lastActive: 'Yesterday',
  },
];

export const TeamPage: React.FC = () => {
  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-helios-text-primary-light dark:text-helios-text-primary-dark">
            Helios Operations Team
          </h2>
          <p className="text-xs text-helios-text-secondary-light dark:text-helios-text-secondary-dark mt-0.5">
            Manage staff members and assign role-based authorization levels.
          </p>
        </div>
        <button
          type="button"
          onClick={() => alert('Invite link generated and sent to email.')}
          className="px-3.5 py-2 text-xs font-semibold rounded-control bg-helios-accent-blue text-white hover:bg-blue-600 transition-colors shadow-sm self-start"
        >
          Invite Team Member
        </button>
      </div>

      <div className="p-6 rounded-card bg-helios-card-light dark:bg-helios-card-dark border border-helios-border-light dark:border-helios-border-dark overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-helios-border-light dark:border-helios-border-dark text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                <th className="pb-3 font-semibold">User</th>
                <th className="pb-3 font-semibold">Assigned Role</th>
                <th className="pb-3 font-semibold">Activity</th>
                <th className="pb-3 font-semibold text-right">Access</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-helios-border-light dark:divide-helios-border-dark text-helios-text-primary-light dark:text-helios-text-primary-dark">
              {teamMembers.map((member) => (
                <tr key={member.id} className="hover:bg-black/5 dark:hover:bg-white/5 transition-colors">
                  <td className="py-3.5">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-helios-accent-blue/10 text-helios-accent-blue flex items-center justify-center font-bold text-xs">
                        {member.name.substring(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <div className="font-semibold">{member.name}</div>
                        <div className="text-[11px] text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                          {member.email}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="py-3.5">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wide uppercase ${
                        member.role === 'admin'
                          ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20'
                          : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                      }`}
                    >
                      {member.role}
                    </span>
                  </td>
                  <td className="py-3.5 text-helios-text-secondary-light dark:text-helios-text-secondary-dark">
                    {member.lastActive}
                  </td>
                  <td className="py-3.5 text-right">
                    <button className="text-xs text-helios-accent-blue hover:underline">
                      Edit Permissions
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
